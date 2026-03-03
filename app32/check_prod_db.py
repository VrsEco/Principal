
import os, sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv('.env')
from app import create_app
from models.agent_message import AgentMessage
from models.agent_action import AgentAction

app = create_app('production')
with app.app_context():
    print('--- MENSAGENS RECENTES (PROD) ---')
    msgs = AgentMessage.query.order_by(AgentMessage.id.desc()).limit(5).all()
    for m in msgs:
        print(f'ID: {m.id} | Canal: {m.channel} | Data: {m.created_at} | Conteúdo: {m.content[:50]}')
    
    print('\n--- TICKETS DE ERRO (PROD) ---')
    actions = AgentAction.query.order_by(AgentAction.id.desc()).limit(5).all()
    for a in actions:
        print(f'ID: {a.id} | Status: {a.status} | Título: {a.title} | Data: {a.created_at}')
