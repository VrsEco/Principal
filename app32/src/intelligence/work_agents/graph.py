from typing import TypedDict, Annotated, List, Literal
from langchain_core.messages import BaseMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
from contextlib import contextmanager

# Imports dos Agentes
from src.intelligence.work_agents.state import WorkAgentState
from src.intelligence.work_agents.agents import get_agent_node, SYSTEM_PROMPTS
from src.intelligence.tool_catalog import tools  # Catálogo único compartilhado
from src.intelligence.work_agents.tool_runtime_guard import build_denied_tool_messages, resolve_state_tool_context

# Supervisor Atualizado
from src.intelligence.agents.supervisor import supervisor_node

# --- 1. Definição do Grafo ---
def create_work_agent_workflow(checkpointer=None):
    """
    Constrói a estrutura do grafo de Agentes de Trabalho (Work Agents V2).
    """
    workflow = StateGraph(WorkAgentState)

    # 2. Adição dos Nós (Agentes)
    workflow.add_node("supervisor", supervisor_node)
    
    # Adiciona cada agente dinamicamente com base no dicionário de prompts
    # Nomes dos nós: 'strategist', 'business_architect', 'operations', 'finance', 'auditor', 'sapiens'
    agent_names = SYSTEM_PROMPTS.keys()
    for name in agent_names:
        workflow.add_node(name, get_agent_node(name))
        
    _base_tool_node = ToolNode(tools)
    def wrapped_tool_node(state: WorkAgentState):
        from src.intelligence.tool_context import get_sapiens_context, set_sapiens_context, reset_sapiens_context
        resolved_state = resolve_state_tool_context(state)
        u = resolved_state.get('user_id')
        c = resolved_state.get('company_id')
        current_context = get_sapiens_context()
        token = set_sapiens_context(
            user_id=u,
            company_id=c,
            employee_id=current_context.employee_id,
            channel=current_context.channel,
            thread_id=current_context.thread_id,
            metadata=current_context.metadata,
        )
        try:
            denied_messages = build_denied_tool_messages(resolved_state)
            if denied_messages:
                return {"messages": denied_messages}
            return _base_tool_node.invoke(resolved_state)
        finally:
            reset_sapiens_context(token)
            
    workflow.add_node("tools", wrapped_tool_node)

    # 3. Definição das Arestas (Estrutura do Fluxo)
    
    # Início -> Supervisor
    workflow.add_edge(START, "supervisor")

    # Supervisor -> Agentes (Roteamento Condicional)
    # A função route_from_supervisor deve estar no supervisor.py ou inline aqui
    def route_from_supervisor(state: WorkAgentState) -> str:
        decision = state.get("next_node", "end")
        # IDs em inglês (padrão v2) e fallbacks em português
        node_map = {
            "strategist": "strategist",
            "estrategista": "strategist",
            "business_architect": "business_architect",
            "negocios": "business_architect",
            "operations": "operations",
            "operacoes": "operations",
            "finance": "finance",
            "financeiro": "finance",
            "auditor": "auditor",
            "sapiens": "sapiens",
            "engineering": "engineering",
            "engenharia": "engineering",
            "end": END
        }
        target_node = node_map.get(decision, END)
        print(f"--- GRAPH ROUTING: Decision '{decision}' -> Node '{target_node}' ---")
        return target_node

    workflow.add_conditional_edges(
        "supervisor",
        route_from_supervisor,
        {
            "strategist": "strategist",
            "business_architect": "business_architect",
            "operations": "operations",
            "finance": "finance",
            "auditor": "auditor",
            "sapiens": "sapiens",
            "engineering": "engineering",
            END: END
        } 
    )

    # Agentes -> Tools ou Supervisor
    def should_continue(state: WorkAgentState) -> Literal["tools", "supervisor"]:
        messages = state["messages"]
        last_message = messages[-1]
        
        # Se for tupla, não tem tool_calls
        if isinstance(last_message, tuple):
            return "supervisor"
            
        # Se o agente chamou uma ferramenta
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            return "tools"
        
        # Se terminou a resposta, volta ao supervisor
        return "supervisor"

    # Conecta todos os agentes à lógica de ferramentas/retorno
    for name in agent_names:
        workflow.add_conditional_edges(
            name,
            should_continue,
            {"tools": "tools", "supervisor": "supervisor"}
        )

    # Tools -> Supervisor (Ciclo Fechado)
    workflow.add_edge("tools", "supervisor")

    return workflow.compile(checkpointer=checkpointer)

# Grafo compilado pronto para uso utilizando persistência centralizada
from src.intelligence.memory import memory_checkpointer
work_agent_graph = create_work_agent_workflow(checkpointer=memory_checkpointer)
