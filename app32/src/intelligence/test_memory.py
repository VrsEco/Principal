import sys
import os

# Adiciona o diretório raiz ao path para permitir imports de src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from langgraph.graph import StateGraph, START, END
from src.intelligence.state import AgentState
from src.intelligence.memory import get_checkpointer
from langchain_core.messages import HumanMessage

def echo_node(state: AgentState):
    """Nó simples que apenas loga o estado e retorna."""
    print(f"--- Executando Nó Echo ---")
    return {"messages": state["messages"]}

def run_test():
    print("Iniciando Teste de Integração de Memória (PostgresSaver)...")
    
    # 1. Configura o Checkpointer (que no v2 retorna um context manager)
    from src.intelligence.memory import get_checkpointer
    
    # 2. Define um Grafo Simples
    workflow = StateGraph(AgentState)
    workflow.add_node("echo", echo_node)
    workflow.add_edge(START, "echo")
    workflow.add_edge("echo", END)

    with get_checkpointer() as checkpointer:
        # Cria as tabelas necessárias se não existirem
        checkpointer.setup()
        
        # 3. Compila o Grafo com Persistência
        app = workflow.compile(checkpointer=checkpointer)

        # 4. Primeira Execução
        thread_id = "test_thread_001"
        config = {"configurable": {"thread_id": thread_id}}
        
        print(f"\nPasso 1: Enviando primeira mensagem para thread {thread_id}...")
        input_message = HumanMessage(content="Oi, eu sou o CTO")
        
        app.invoke({"messages": [input_message]}, config=config)
        print("Mensagem enviada e processada.")

        # 5. Segunda Execução (Verificação de Persistência)
        print(f"\nPasso 2: Recuperando estado da thread {thread_id}...")
        state = app.get_state(config)
        
        if state.values and "messages" in state.values:
            messages = state.values["messages"]
            last_msg = messages[-1].content
            print(f"Estado recuperado! Última mensagem: '{last_msg}'")
            
            if last_msg == "Oi, eu sou o CTO":
                print("\nSUCESSO: O PostgresSaver salvou e recuperou o histórico corretamente!")
            else:
                print("\nFALHA: A mensagem recuperada é diferente da enviada.")
        else:
            print("\nFALHA: Não foi possível recuperar o estado do banco de dados.")

if __name__ == "__main__":
    run_test()
