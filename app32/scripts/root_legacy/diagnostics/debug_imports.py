import os
import sys
sys.path.append(os.getcwd())
try:
    print("Importing state...")
    from src.intelligence.work_agents.state import WorkAgentState
    print("Importing agents...")
    from src.intelligence.work_agents.agents import get_agent_node, SYSTEM_PROMPTS
    print("Importing supervisor...")
    from src.intelligence.agents.supervisor import supervisor_node
    print("Importing graph...")
    from src.intelligence.work_agents.graph import work_agent_graph
    print("✅ TODO IMPORTADO COM SUCESSO")
except Exception:
    import traceback
    traceback.print_exc()
