from typing import Literal
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode

from src.intelligence.state import AgentState
from src.intelligence.agents.supervisor import supervisor_node
from src.intelligence.agents.expert import expert_node
from src.intelligence.agents.specialists import fiscal_node, financeiro_node
from src.intelligence.runtime_guard import require_legacy_runtime_access
from src.intelligence.tool_catalog import tools

def create_agent_workflow():
    """
    Constrói a estrutura do grafo de agentes utilizando o padrão Supervisor-Worker.
    Retorna o objeto workflow (ainda não compilado).
    """
    require_legacy_runtime_access(
        module="src.intelligence.graph.create_agent_workflow",
        operation="create_workflow",
    )
    workflow = StateGraph(AgentState)

    # 1. Adição dos Nós
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("expert", expert_node)
    workflow.add_node("fiscal", fiscal_node)
    workflow.add_node("financeiro", financeiro_node)
    workflow.add_node("tools", ToolNode(tools))

    # 2. Definição das Arestas (Estrutura do Fluxo)
    
    # Início sempre pelo supervisor
    workflow.add_edge(START, "supervisor")

    # Aresta condicional saindo do Supervisor
    def route_from_supervisor(state: AgentState) -> Literal["expert", "fiscal", "financeiro", "end"]:
        return state.get("next_node", "end")

    workflow.add_conditional_edges(
        "supervisor",
        route_from_supervisor,
        {
            "expert": "expert",
            "fiscal": "fiscal",
            "financeiro": "financeiro",
            "end": END
        }
    )

    # Função condicional genérica para especialistas
    def should_continue(state: AgentState) -> Literal["tools", "supervisor"]:
        messages = state["messages"]
        last_message = messages[-1]
        
        # Se o modelo gerou chamadas de ferramenta
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            return "tools"
        
        # Se já gerou uma resposta textual, volta ao supervisor
        return "supervisor"

    # Conecta todos os especialistas à lógica de continuação
    for node_name in ["expert", "fiscal", "financeiro"]:
        workflow.add_conditional_edges(
            node_name,
            should_continue,
            {
                "tools": "tools",
                "supervisor": "supervisor"
            }
        )

    # Aresta saindo das Ferramentas: Volta para o Supervisor para que ele decida o próximo passo
    # (Com o resultado da ferramenta no histórico, o supervisor provavelmente chamará o especialista de novo ou encerrará)
    workflow.add_edge("tools", "supervisor")

    return workflow

# Workflow base pronto para compilação
agent_workflow = create_agent_workflow()
