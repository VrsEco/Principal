from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, END, START
from agents.state import BoardState
from agents.board.supervisor import supervisor_node
from agents.board.cso import cso_node
from agents.board.skeptic import skeptic_node
from agents.board.coo import coo_node
from agents.onboarding.interviewer import onboarding_interviewer_node

def human_approval_node(state: BoardState):
    """
    Nó de pausa para intervenção humana.
    """
    # Este nó não faz nada; a interrupção acontece ANTES dele ser executado
    return state

def create_board_graph():
    """
    Montagem da arquitetura de Orquestração Hierárquica do Gestão Versus.
    """
    
    # 1. Inicializa o Grafo com o esquema de estado definido
    workflow = StateGraph(BoardState)

    # 2. Adiciona os Nós (Nodes)
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("CSO", cso_node)
    workflow.add_node("Skeptic", skeptic_node)
    workflow.add_node("COO", coo_node)
    workflow.add_node("ONBOARDING", onboarding_interviewer_node)
    workflow.add_node("human_approval", human_approval_node)

    # 3. Definição das Arestas (Edges)
    # Entrada principal vai para o Supervisor
    workflow.add_edge(START, "supervisor")

    # Arestas de especialistas sempre voltam para o Supervisor para reavaliação do fluxo
    workflow.add_edge("CSO", "supervisor")
    workflow.add_edge("Skeptic", "supervisor")
    workflow.add_edge("COO", "supervisor")
    workflow.add_edge("ONBOARDING", "supervisor")
    workflow.add_edge("human_approval", "supervisor")

    # 4. Lógica de Roteamento (Aresta Condicional do Supervisor)
    def router(state: BoardState):
        """
        Lê a decisão do Supervisor no estado e direciona o fluxo.
        """
        next_node = state.get("next_node")
        
        if next_node == "FINISH":
            return END
        
        # Mapeia a string do supervisor para o nome do nó
        return next_node

    workflow.add_conditional_edges(
        "supervisor",
        router,
        {
            "CSO": "CSO",
            "Skeptic": "Skeptic",
            "COO": "COO",
            "ONBOARDING": "ONBOARDING",
            "HUMAN_APPROVAL": "human_approval",
            "FINISH": END
        }
    )

    # 5. Compilação do Grafo com Checkpointer para persistência de estado e HITL
    memory = MemorySaver()
    app = workflow.compile(
        checkpointer=memory,
        interrupt_before=["human_approval"]
    )
    
    return app

# Instância global do cérebro orquestrado
board_intelligence = create_board_graph()

if __name__ == "__main__":
    # Teste de visualização (opcional)
    print("Grafo do Board compilado com sucesso.")
    # Se quiser imprimir a estrutura em ascii (requer pygraphviz ou similar)
    # print(board_intelligence.get_graph().draw_ascii())
