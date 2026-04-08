import sys
import os

# Adiciona a raiz ao path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import HumanMessage

from src.intelligence.state import AgentState
from src.intelligence.agents.supervisor import supervisor_node
from src.intelligence.agents.expert import expert_node
from src.intelligence.tool_catalog import tools
from src.intelligence.memory import get_checkpointer

def run_integration_test():
    print("\n=== INICIANDO TESTE DE INTEGRAÇÃO DO AGENTE (SUPERVISOR-EXPERT) ===")
    
    # Pergunta que exige consulta ao RAG (conforme seed anterior)
    pergunta = "Qual a regra para notas fiscais acima de R$ 10.000?"
    thread_id = "test_agent_001"
    
    print(f"Pergunta: {pergunta}")
    print(f"Thread: {thread_id}")

    # Montagem local do grafo para garantir que o checkpointer esteja ativo no contexto
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

    try:
        with get_checkpointer() as checkpointer:
            app = workflow.compile(checkpointer=checkpointer)
            
            config = {"configurable": {"thread_id": thread_id}}
            
            print("\n--- Iniciando Fluxo do Grafo ---")
            for chunk in app.stream({"messages": [HumanMessage(content=pergunta)]}, config=config, stream_mode="values"):
                if "messages" in chunk:
                    last_msg = chunk["messages"][-1]
                    role = "Assistant" if last_msg.type == "ai" else "Human"
                    # Se for AI com tool_calls, mostra as chamadas
                    if getattr(last_msg, 'tool_calls', None):
                        print(f"[{role}] chamando ferramentas: {[t['name'] for t in last_msg.tool_calls]}")
                    else:
                        content_info = (last_msg.content[:100] + '...') if len(last_msg.content) > 100 else last_msg.content
                        print(f"[{role}]: {content_info}")

            print("\n--- Teste Concluído com Sucesso ---")
            
    except Exception as e:
        print(f"\nERRO DURANTE O TESTE: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_integration_test()
