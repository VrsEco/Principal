
from app import create_app
from models.agent_action import AgentAction
import os

os.environ['TELEGRAM_SETUP_WEBHOOK'] = 'false'
app = create_app('development')
with app.app_context():
    actions = AgentAction.query.order_by(AgentAction.id.desc()).limit(3).all()
    print("Recent Agent Actions:")
    for a in actions:
        print(f"ID: {a.id} | Title: {a.title} | Company: {a.company_id} | Status: {a.status}")
