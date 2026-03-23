
import os, sys
sys.path.append(os.getcwd())
from src.intelligence.agents.supervisor import supervisor_node
from src.intelligence.work_agents.state import WorkAgentState
from langchain_core.messages import HumanMessage

def test_router():
    state = {
        "messages": [HumanMessage(content="traga para mim as atividades em aberto de Caroline Marques da empresa Gandu Investimentos")],
        "next_node": None
    }
    result = supervisor_node(state)
    print(f"Decision: {result.get('next_node')}")
    if "messages" in result:
        print(f"Direct Response: {result['messages'][0].content}")

if __name__ == "__main__":
    test_router()
