
import os, sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv('.env')
from app import create_app
from models.agent_message import AgentMessage
from sqlalchemy import desc

app = create_app('production')
with app.app_context():
    try:
        messages = AgentMessage.query.order_by(desc(AgentMessage.id)).limit(2).all()
        for m in messages:
            print(f"MSG_{m.id}_START")
            print(f"DIR: {m.direction}")
            print(f"FROM: {m.agent_name}")
            print(f"CONTENT: {m.content}")
            print(f"DATE: {m.created_at}")
            print(f"MSG_{m.id}_END")
    except Exception as e:
        print(f"Error fetching: {e}")
