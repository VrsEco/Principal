import sys
sys.path.append('.')

from app import create_app
from models.agent_action import AgentAction

app = create_app('production')

with app.app_context():
    actions = AgentAction.query.order_by(AgentAction.created_at.desc()).limit(3).all()
    for act in actions:
        print(f"[{act.created_at}] ID: {act.id} | Type: {act.type}")
        print(f"Desc: {act.description}")
        print(f"Payload: {act.payload}")
        print("-" * 50)
