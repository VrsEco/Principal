
import os
import sys
# Path setup
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from app import create_app
from models.agent_action import AgentAction
import json

app = create_app()
with app.app_context():
    print("\n--- ÚLTIMOS ERROS ESCALONADOS (Técnicos) ---")
    actions = AgentAction.query.filter_by(type='technical_fix').order_by(AgentAction.id.desc()).limit(5).all()
    if not actions:
        print("Nenhum erro encontrado.")
    for a in actions:
        print(f"Ticket #{a.id} | Status: {a.status} | Agente: {a.requesting_agent}")
        print(f"Título: {a.title}")
        print(f"Descrição: {a.description}")
        print(f"Payload (traced): {json.dumps(a.payload, indent=2)}")
        print("-" * 40)
