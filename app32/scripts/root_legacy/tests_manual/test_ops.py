
import os, sys
sys.path.append(os.getcwd())
from src.intelligence.work_agents.agents import get_agent_node
from src.intelligence.work_agents.state import WorkAgentState
from langchain_core.messages import HumanMessage, AIMessage

def test_operations():
    # Mocking active user context for the tool (Fabiano = 3, main_emp=30)
    os.environ['ACTIVE_USER_ID'] = '3'
    os.environ['ACTIVE_COMPANY_ID'] = '7'
    
    agent = get_agent_node("operations")
    state = {
        "messages": [
            HumanMessage(content="traga para mim as atividades em aberto de Caroline Marques da empresa Gandu Investimentos")
        ]
    }
    
    # Run the agent node
    result = agent(state)
    msg = result["messages"][0]
    print(f"Agent content: {msg.content}")
    print(f"Tool calls: {msg.tool_calls}")

if __name__ == "__main__":
    test_operations()
