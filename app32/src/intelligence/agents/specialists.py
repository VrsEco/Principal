from langchain_core.messages import SystemMessage
from src.intelligence.llm import llm_expert
from src.intelligence.tool_catalog import tools

def create_agent_node(agent_name: str, system_prompt: str):
    """
    Cria um nó de grafo para um agente especialista específico.
    """
    model_with_tools = llm_expert.bind_tools(tools)

    def agent_node(state):
        messages = state["messages"]
        # Injeta o contexto do especialista no início se necessário, 
        # ou apenas mantém o histórico.
        sys_msg = SystemMessage(content=system_prompt)
        
        # Filtra para não duplicar system message se já houver uma no histórico (opcional)
        response = model_with_tools.invoke([sys_msg] + messages)
        
        return {"messages": [response]}

    return agent_node

# --- Definições de Prompts ---

FISCAL_PROMPT = """Você é o Especialista Fiscal do Gestão Versus.
Sua missão é analisar dados contábeis, impostos e conformidade.
Você tem acesso ao banco de dados para consultar informações reais da empresa.
Sempre seja preciso e cite os dados encontrados."""

FINANCEIRO_PROMPT = """Você é o Especialista Financeiro do Gestão Versus.
Sua missão é analisar fluxo de caixa, rentabilidade e projeções financeiras.
Ajude o usuário a entender a saúde financeira da empresa com base nos dados do sistema."""

# --- Nodes ---
fiscal_node = create_agent_node("fiscal", FISCAL_PROMPT)
financeiro_node = create_agent_node("financeiro", FINANCEIRO_PROMPT)
