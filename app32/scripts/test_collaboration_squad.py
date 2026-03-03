import os
import sys

# Ajusta o path para encontrar o código da src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from src.intelligence.work_agents.graph import work_agent_graph
from langchain_core.messages import HumanMessage

def test_squad_collaboration():
    print("TESTE DE COLABORACAO MULTI-AGENTE (SQUAD V2.0)")

    # Contexto Inicial
    initial_state = {
        "messages": [
            HumanMessage(content="Quero expandir minha receita vendendo para o setor público através de licitações. Defina meus OKRs para o próximo trimestre e como devo estruturar minha área de licitações para suportar isso.")
        ],
        "user_id": 1,
        "company_id": 1,
        "collaboration_count": 0,
        "context_data": {}
    }

    # Configuração da Thread (Persistence)
    config = {"configurable": {"thread_id": "test_collaboration_thread"}}

    print(f"\n[DEMANDA]: {initial_state['messages'][0].content}\n")

    # Executa o Grafo
    for event in work_agent_graph.stream(initial_state, config):
        for node, values in event.items():
            print(f"\n--- ATIVIDADE NO NÓ: {node} ---")
            if "messages" in values:
                last_msg = values["messages"][-1]
                # Se for AI Message, imprime o conteúdo
                if hasattr(last_msg, 'content') and last_msg.content:
                    print(f"[{node.upper()}]: {last_msg.content[:300]}...")
            
            if "next_node" in values:
                print(f"[{node.upper()} DECISION]: Próximo -> {values['next_node']}")
            
            if "collaboration_count" in values:
                print(f"[COLLABORATION COUNT]: {values['collaboration_count']}")

    print("\n" + "="*80)
    print("FIM DO TESTE DE COLABORACAO")
    print("="*80)

if __name__ == "__main__":
    test_squad_collaboration()
