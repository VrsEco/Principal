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
        # Por simplicidade neste grafo v2, o Supervisor pode redelegar ou usar o histórico
        print("--- SUPERVISOR: Ferramenta executada, devolvendo ao especialista para conclusão. ---")
        # Vamos usar a lógica de roteamento abaixo para decidir, mas garantindo que não seja 'end'
    
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
        "1. 'strategist' (Estrategista): Para Planejamento Estratégico, Análise de Mercado, Cenários, SWOT e OKRs visionários.\n"
        "2. 'business_architect' (Arquiteto de Negócios): Para Mapeamento de Processos, Organograma, Eficiência e Maturidade Empresarial.\n"
        "3. 'operations' (Operações/COO): Para Prazos, Gestão de Projetos, Cobrança de Tarefas e Monitoramento de Metas/KPIs.\n"
        "4. 'finance' (Financeiro/CFO): Para DRE, Fluxo de Caixa, Balanço, Viabilidade (VPL/TIR), Custos e Precificação.\n"
        "5. 'auditor' (Auditor/Compliance): Para Auditoria de TRANSAÇÕES de negócio, Riscos Operacionais e Conformidade com Processos.\n"
        "6. 'sapiens' (Onboarding & Manual Vivo): Para dúvidas de uso do sistema, cadastros assistidos, saudações e 'Como fazer X?' (Manual de Operações).\n"
        "7. 'engineering' (Engenharia): Para reporte de bugs, erros de sistema, tracebacks, falhas técnicas e problemas de banco de dados.\n"
        "8. 'end': Use apenas se a conversa estiver CLARAMENTE encerrada com um 'tchau' ou 'adeus'.\n\n"
        
        "DIRETRIZ DE CONFLITO:\n"
        "- Se o usuário disser 'Oi', 'Olá' ou fizer perguntas gerais sobre o sistema, USE 'sapiens'.\n"
        "- Se o usuário colar um erro técnico (traceback) ou mencionar 'bug', 'falha' ou 'erro', USE 'engineering'.\n"
        "- Se for análise de dados financeiros, USE 'finance'.\n"
        "- Se for cobrança ou prazo, USE 'operations'.\n\n"
        
        "Responda EXCLUSIVAMENTE com o ID do agente: 'strategist', 'business_architect', 'operations', 'finance', 'auditor', 'sapiens', 'engineering' ou 'end'."
    )
    
    # Invoca o LLM Router (gpt-4o-mini geralmente)
    response = llm_router.invoke([
        SystemMessage(content=system_prompt)
    ] + messages)
    
    decision = response.content.lower().strip()
    
    # Validação/Mapping de Segurança
    valid_nodes = ["strategist", "business_architect", "operations", "finance", "auditor", "sapiens", "engineering", "end"]
    next_node = "end"
    
    for node in valid_nodes:
        if node in decision:
            next_node = node
            break

    # HEURÍSTICA DE REFORÇO: Se o supervisor decidir 'end' mas houver sinais de comando na mensagem,
    # forçamos para o Sapiens ou Operations para evitar o 'eco' do fallback.
    if isinstance(last_message, tuple):
        text_content = last_message[1].lower()
    else:
        text_content = getattr(last_message, 'content', '').lower()
        
    command_signals = ['http', 'tela', 'alterar', 'mudar', 'status', 'inativa', 'cadastrar', 'criar', 'desativar', 'erro', 'bug', 'falha']
    if next_node == "end" and any(sig in text_content for sig in command_signals):
        print(f"--- SUPERVISOR: Detectado sinal de comando em '{next_node}'. Forçando 'operations' ou 'engineering'. ---")
        next_node = "engineering" if 'erro' in text_content or 'bug' in text_content else "operations"

    # REGRA CRÍTICA: O Supervisor nunca deve retornar 'end' sem ter passado por um agente.
    # Se não há mensagem de IA no histórico, forçamos para sapiens.
    has_ai_response = any(
        (hasattr(m, 'type') and m.type == 'ai') or (isinstance(m, tuple) and m[0] == 'assistant')
        for m in messages
    )
    if next_node == "end" and not has_ai_response:
        print("--- SUPERVISOR: Sem resposta AI ainda, forçando 'sapiens'. ---")
        next_node = "sapiens"

    print(f"--- SUPERVISOR DECISION: {next_node} ---")
    return {"next_node": next_node}
