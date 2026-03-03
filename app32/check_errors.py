
import os, sys
# Ensure app root is in path
sys.path.append(os.getcwd())

from app import create_app
from models.agent_action import AgentAction
import json

def check():
    app = create_app()
    with app.app_context():
        # Get last 3 error actions
        actions = AgentAction.query.filter_by(type='technical_fix').order_by(AgentAction.id.desc()).limit(3).all()
        if not actions:
            print("Nenhum erro registrado.")
            return
        for a in actions:
            print(f"Ticket #{a.id}")
            print(f"Descrição: {a.description}")
            print(f"Payload: {a.payload}")
            print("-" * 50)

if __name__ == "__main__":
    check()
