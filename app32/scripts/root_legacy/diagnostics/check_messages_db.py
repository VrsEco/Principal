
import os
import sys
from app import create_app
from models.agent_message import AgentMessage

print("Checking recent messages in LOCAL DB...")
os.environ['TELEGRAM_SETUP_WEBHOOK'] = 'false'
app = create_app('development')
with app.app_context():
    msgs = AgentMessage.query.order_by(AgentMessage.id.desc()).limit(10).all()
    if not msgs:
        print("No messages found in local DB.")
    else:
        for m in msgs:
            print(f"ID: {m.id} | Date: {m.created_at} | Content: {m.content[:50]}...")
