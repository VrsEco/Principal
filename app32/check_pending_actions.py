from app import app
from models.agent_action import AgentAction

def check_actions():
    with app.app_context():
        actions = AgentAction.query.filter_by(status='pending').all()
        print(f"Total de ações pendentes: {len(actions)}")
        for a in actions:
            print(f"ID: {a.id} | Tipo: {a.type} | Título: {a.title} | Descrição: {a.description}")

if __name__ == "__main__":
    check_actions()
