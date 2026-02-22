import sys, os
sys.path.append(os.getcwd())
try:
    from src.intelligence.work_agents.agents import SYSTEM_PROMPTS
except:
    import traceback
    with open("error_full.txt", "w") as f:
        traceback.print_exc(file=f)
    traceback.print_exc()
