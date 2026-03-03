
import os, sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv('.env')
from app import create_app
from models.agent_message import AgentMessage
from sqlalchemy import desc

app = create_app('production')
with app.app_context():
    print("--- RECENT AGENT MESSAGES ---")
    messages = AgentMessage.query.order_by(desc(AgentMessage.id)).limit(5).all()
    for m in messages:
        print(f"ID: {m.id} | Dir: {m.direction} | From: {m.agent_name} | Content: {m.content[:100]} | Date: {m.created_at}")
    
    print("\n--- RECENT ERRORS (AgentAction) ---")
    from models.agent_action import AgentAction
    actions = AgentAction.query.order_by(desc(AgentAction.id)).limit(3).all()
    for a in actions:
        print(f"ID: {a.id} | Status: {a.status} | Title: {a.title} | Error: {a.payload.get('error') if a.payload else 'N/A'}")
