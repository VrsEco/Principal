
from app import create_app
from models import db, AgentAction, AgentMessage, User
import json

app = create_app('production')
with app.app_context():
    print("\n--- [AUDITORIA TECNICA DO TELEGRAM] ---")
    
    # 1. Verificar se houve crash registrado no AgentAction
    actions = AgentAction.query.filter_by(requesting_agent='telegram_webhook').order_by(AgentAction.id.desc()).limit(5).all()
    if actions:
        print(f"Encontrados {len(actions)} crashes registrados:")
        for a in actions:
            print(f"\nTicket #{a.id} - {a.title}")
            print(f"Erro: {a.description}")
            if a.payload and 'traceback' in a.payload:
                print(f"Traceback:\n{a.payload['traceback']}")
    else:
        print("Nenhum crash formal registrado via AgentAction.")

    # 2. Verificar se a mensagem entrou na tabela Geral de mensagens
    # (Para ver se o usuario está sendo identificado)
    msgs = AgentMessage.query.order_by(AgentMessage.id.desc()).limit(5).all()
    if msgs:
        print("\nUltimas mensagens no canal Telegram:")
        for m in msgs:
            print(f"ID: {m.id} | De: {m.agent_name} | Conteudo: {m.content[:50]}...")
    
    # 3. Verificar Vinculo de Usuarios com Telegram
    linked_users = User.query.filter(User.telegram.isnot(None)).all()
    print(f"\nUsuarios vinculados ao Telegram: {len(linked_users)}")
    for u in linked_users:
        print(f"U: {u.name} | Telegram: {u.telegram}")
