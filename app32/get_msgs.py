import sys
sys.path.append('.')

from app import create_app
from models import AgentMessage

app = create_app('production')

with app.app_context():
    msgs = AgentMessage.query.order_by(AgentMessage.created_at.desc()).limit(10).all()
    for m in msgs:
        print(f"[{m.created_at}] Dir: {m.direction} | AgentType: {m.agent_type} | Name: {m.agent_name}")
        print(f"Content: {m.content}")
        print("Meta:", m.metadata_json)
        print("-" * 50)
