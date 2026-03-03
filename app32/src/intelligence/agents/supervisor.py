import json
from langchain_core.messages import SystemMessage, HumanMessage
from src.intelligence.llm import llm_router
from src.intelligence.work_agents.state import WorkAgentState

def supervisor_node(state: WorkAgentState):
    """
    Nó Supervisor (Roteador Central - Work Agents V2).
    Analisa a mensagem do usuário e decide para qual dos 6 Agentes de Trabalho (ou END) deve encaminhar.
    """
    messages = state["messages"]
    last_message = messages[-1]

    # Normaliza o tipo da mensagem (pode ser tupla ou BaseMessage)
    msg_type = ""
    if isinstance(last_message, tuple):
        msg_type = last_message[0]
    elif hasattr(last_message, 'type'):
        msg_type = last_message.type

    # Se a última mensagem veio de uma AI (Agente Especialista) e não é uma chamada de ferramenta,
    # significa que o especialista já respondeu. O Supervisor deve entregar ao usuário (END).
    is_ai = msg_type == "ai"
    has_tools = getattr(last_message, 'tool_calls', None) if not isinstance(last_message, tuple) else False
    
    if is_ai and not has_tools:
        print("--- SUPERVISOR: Resposta final do especialista recebida, encerrando fluxo. ---")
        return {"next_node": "end"}
    
    # Se a última mensagem é do tipo 'tool', significa que uma ferramenta acabou de rodar.
    if msg_type == "tool":
        # Tenta identificar qual foi o último agente que falou antes da tool
        print("--- SUPERVISOR: Ferramenta executada, devolvendo ao especialista para conclusão. ---")
        last_agent = state.get("next_node")
        if last_agent and last_agent != "end":
            print(f"--- SUPERVISOR DECISION (RETORNO): {last_agent} ---")
            return {"next_node": last_agent}
        # Se por algum motivo não tiver, segue o fluxo normal
    
    # Prompt de Roteamento Avançado
    system_prompt = (
        "Você é o Supervisor Central do Ecossistema Gestão Versus. Sua função é orquestrar o atendimento.\n"
        "Analise a solicitação do usuário e encaminhe para o Agente Especialista mais adequado:\n\n"
        
        "LEI DE CONFORMIDADE ARQUITETURAL (INVIOLAVEL):\n"
        "- MUTACAO DE DADOS (criar, editar, excluir, registrar): O agente DEVE usar as ferramentas "
        "MCP que espelham os Models do app (ORM). NUNCA invente dados ou grave fora da estrutura do sistema.\n"
        "- ANALISE DE DADOS (consultar, cruzar, calcular): O agente PODE usar query_database() livremente "
        "com SQL SELECT. Isso equivale a um humano analisando relatorios.\n"
        "- PRINCIPIO: Tudo que o Sapiens faz deve ser visivel e editavel pelo usuario humano no app.\n\n"
        
        "AGENTES DISPONÍVEIS:\n"
        "1. 'strategist' (Estrategista): Para Planejamento Estratégico, Visão, OKRs de longo prazo e análise de mercado.\n"
        "2. 'business_architect' (Arquiteto de Negócios): Para Mapeamento de PROCESSOS, Áreas, Hierarquias e Eficiência.\n"
        "3. 'operations' (Operações/COO): Para TAREFAS, ATIVIDADES, PRAZOS, cobrar entregas, consultar o que está em aberto, o que vence hoje/amanhã, e gestão de equipes.\n"
        "4. 'finance' (Financeiro/CFO): Para DRE, Fluxo de Caixa, Balanço e Custos.\n"
        "5. 'auditor' (Auditor/Compliance): Para Auditoria de transações e riscos.\n"
        "6. 'sapiens' (Onboarding & Manual Vivo): Para dúvidas de USO do sistema, saudações, ajuda geral e manual de operações.\n"
        "7. 'engineering' (Engenharia): Para bugs, erros técnicos e falhas.\n"
        "8. 'end': Use apenas no final absoluto da conversa.\n\n"
        
        "DIRETRIZ DE DECISÃO:\n"
        "- Perguntas sobre 'quem tem tal tarefa?', 'o que tenho para hoje?', 'atividades de fulano' -> SEMPRE 'operations'.\n"
        "- 'Oi', 'Quem é você?' -> 'sapiens'.\n"
        "- 'Como cadastro um cliente?' -> 'sapiens'.\n"
        
        "Responda EXCLUSIVAMENTE com o ID do agente: 'strategist', 'business_architect', 'operations', 'finance', 'auditor', 'sapiens', 'engineering' ou 'end'."
    )
    
    # Invoca o LLM Router (gpt-4o para maior precisão no roteamento)
    from pydantic import BaseModel, Field
    from src.intelligence.llm import llm_expert  # Mudamos para llm_expert (@ARQUITETO)
    
    class RouteDecision(BaseModel):
        destination: str = Field(description="Exatamente um destes valores: strategist, business_architect, operations, finance, auditor, sapiens, engineering, end")

    llm_structured = llm_expert.with_structured_output(RouteDecision)
    
    try:
        response_data = llm_structured.invoke([
            SystemMessage(content=system_prompt)
        ] + messages)
        decision = response_data.destination.lower().strip()
    except Exception as e:
        print(f"--- SUPERVISOR: Erro ao fazer parsing estruturado: {e}. Fallback para LLM padrão. ---")
        from src.intelligence.llm import llm_router
        response = llm_router.invoke([SystemMessage(content=system_prompt)] + messages)
        decision = response.content.lower().strip()
    
    # Validação/Mapping de Segurança
    valid_nodes = ["strategist", "business_architect", "operations", "finance", "auditor", "sapiens", "engineering", "end"]
    next_node = "end"
    
    for node in valid_nodes:
        if node in decision:
            next_node = node
            break

    # HEURÍSTICA DE REFORÇO: 
    # 1. Se o supervisor decidir 'end' mas houver sinais de comando ou SAUDAÇÃO na mensagem,
    # forçamos para o Sapiens ou Operations para evitar o 'eco' do fallback.
    if isinstance(last_message, tuple):
        text_content = last_message[1].lower()
    else:
        text_content = last_message.content.lower()
        
    greetings = ['oi', 'ola', 'olá', 'bom dia', 'boa tarde', 'boa noite', 'ei', 'sapien', 'sapiens']
    # Adicionado 'tarefa', 'atividade', 'pendencia', 'aberto' aos sinais de comando
    command_signals = [
        'http', 'tela', 'alterar', 'mudar', 'status', 'inativa', 'cadastrar', 'criar', 
        'desativar', 'erro', 'bug', 'falha', 'tarefa', 'atividade', 'atividades', 
        'pendencia', 'pendencia', 'aberto', 'abertas', 'vencido', 'vencida'
    ]
    
    if next_node == "end":
        if any(greet in text_content for greet in greetings):
            print(f"--- SUPERVISOR: Saudação detectada. Forçando 'sapiens'. ---")
            next_node = "sapiens"
        elif any(sig in text_content for sig in command_signals):
            print(f"--- SUPERVISOR: Detectado sinal de comando em '{next_node}'. Forçando 'operations'. ---")
            next_node = "engineering" if any(x in text_content for x in ['erro', 'bug', 'falha']) else "operations"

    print(f"--- SUPERVISOR DECISION: {next_node} ---")
    return {"next_node": next_node}

