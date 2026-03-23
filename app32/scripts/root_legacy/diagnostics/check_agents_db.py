
import sys
import os
sys.path.append(os.getcwd())
try:
    from app import create_app
    from models.ai_agent import AIAgent
    app = create_app()
    with app.app_context():
        agents = AIAgent.query.all()
        print(f"COUNT AGENTS: {len(agents)}")
        for a in agents:
            print(f"ID: {a.id}, NAME: {a.name}")
except Exception as e:
    print(f"ERROR: {e}")
