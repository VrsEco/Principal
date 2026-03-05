import os
import sys

# Ensure app is in path
sys.path.append('.')

from app import create_app
from src.intelligence.work_agents.graph import create_work_agent_workflow
from src.intelligence.memory import get_checkpointer

app = create_app('production')

with app.app_context():
    with get_checkpointer() as checkpointer:
        graph = create_work_agent_workflow(checkpointer=checkpointer)
        inputs = {
            "messages": [("user", "quais atividades Caroline Marques da empresa Gandu Investimentos tem em aberto?")],
            "user_id": 1,
            "company_id": 1
        }
        config = {"configurable": {"thread_id": "test_graph_debug_001"}}
        
        try:
            for event in graph.stream(inputs, config=config):
                print("--- EVENT ---")
                print(event)
        except Exception as e:
            print("ERROR:", e)
