import sys
import os
from unittest.mock import MagicMock

# Adiciona a raiz ao path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import HumanMessage, AIMessage
from langchain_community.chat_models import FakeListChatModel

from src.intelligence.state import AgentState
from src.intelligence.agents.supervisor import supervisor_node
from src.intelligence.agents.expert import expert_node
from src.intelligence.tools import tools
from src.intelligence.memory import get_checkpointer

def run_mock_test():
    print("\n=== TESTE DE FLUXO (SIMULADO) - VALIDAÇÃO DE ARQUITETURA ===")
    
    # 1. Criamos mocks separados para cada papel
    mock_router = MagicMock()
    mock_router.invoke.side_effect = [
        AIMessage(content="expert"), # 1ª volta: Supervisor decide rotear
        AIMessage(content="end")     # 2ª volta: Especialista resolveu, supervisor encerra
    ]

    mock_expert_model = MagicMock()
    mock_expert_model.invoke.side_effect = [
        AIMessage(content="", tool_calls=[{"name": "consult_rules", "args": {"query": "notas acima de 10k"}, "id": "call_1", "type": "tool_call"}]), 
        AIMessage(content="De acordo com as regras internas (RAG), notas fiscais acima de R$ 10.000 exigem a aprovação de dois diretores financeiros.")
    ]
    
    # Injetamos os mocks nos módulos
    import src.intelligence.agents.supervisor as supervisor_mod
    import src.intelligence.agents.expert as expert_mod
    
    supervisor_mod.llm_router = mock_router
    expert_mod.model_with_tools = mock_expert_model

    # 2. Montamos o Grafo
    workflow = StateGraph(AgentState)
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("expert", expert_node)
    workflow.add_node("tools", ToolNode(tools))

    workflow.add_edge(START, "supervisor")
    
    def route_supervisor(state):
        return state.get("next_node", "end")
    workflow.add_conditional_edges("supervisor", route_supervisor, {"expert": "expert", "end": END})

    def route_expert(state):
        if state["messages"][-1].tool_calls:
            return "tools"
        return "supervisor"
    workflow.add_conditional_edges("expert", route_expert, {"tools": "tools", "supervisor": "supervisor"})
    workflow.add_edge("tools", "expert")

    # 3. Execução
    thread_id = "mock_thread_v2"
    print(f"Iniciando jornada para Thread: {thread_id}\n")

    try:
        with get_checkpointer() as checkpointer:
            app = workflow.compile(checkpointer=checkpointer)
            config = {"configurable": {"thread_id": thread_id}}
            
            input_msg = "Qual a regra para notas acima de 10k?"
            print(f"[Usuário]: {input_msg}")

            for event in app.stream({"messages": [HumanMessage(content=input_msg)]}, config=config):
                for node_name, state_update in event.items():
                    print(f"\n>> NÓ EXECUTADO: {node_name}")
                    if "messages" in state_update:
                        msg = state_update["messages"][-1]
                        if hasattr(msg, 'tool_calls') and msg.tool_calls:
                            print(f"[Expert]: Solicitou ferramenta -> {msg.tool_calls[0]['name']}")
                        else:
                            print(f"[{node_name.capitalize()}]: {msg.content}")
                    if "next_node" in state_update:
                        print(f"[Decisão]: Próximo nó será -> {state_update['next_node']}")

        print("\n=== VALIDAÇÃO CONCLUÍDA: O FLUXO SUPERVISOR-WORKER ESTÁ OPERALIZADO! ===")
        
    except Exception as e:
        print(f"Erro no teste: {e}")

if __name__ == "__main__":
    run_mock_test()
