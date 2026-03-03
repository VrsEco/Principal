
import os, sys
sys.path.append(os.getcwd())
from app import create_app
from models.agent_action import AgentAction
from datetime import datetime, timedelta

def check():
    app = create_app()
    with app.app_context():
        # Last 10 technical errors in the last 2 hours
        since = datetime.utcnow() - timedelta(hours=2)
        actions = AgentAction.query.filter(
            AgentAction.type == 'technical_fix',
            AgentAction.created_at >= since
        ).order_by(AgentAction.id.desc()).all()
        
        print(f"\n--- ERROS NAS ÚLTIMAS 2 HORAS: {len(actions)} ---")
        for a in actions:
            print(f"Ticket #{a.id} | Criado: {a.created_at}")
            print(f"Propriedades: {a.payload.get('telegram_id', 'N/A')}")
            print(f"Erro: {a.description}")
            print("-" * 30)

if __name__ == "__main__":
    check()
