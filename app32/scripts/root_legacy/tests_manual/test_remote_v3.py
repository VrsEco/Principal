
import os
import sys
import telebot
from app import create_app

# Simulation Script for Server
def test_webhook_crash_prevention():
    os.environ['TELEGRAM_SETUP_WEBHOOK'] = 'false'
    app = create_app('production')
    with app.app_context():
        from api.webhooks.telegram_webhook import process_telegram_message
        from models.agent_action import AgentAction
        from models import db
        
        # Simular uma mensagem de um ID que NÃO existe no banco
        class MockMessage:
            def __init__(self):
                self.text = "teste servidor"
                self.from_user = type('U', (), {'id': 111222333, 'first_name': 'ServerTest'})()
                self.chat = type('C', (), {'id': 111222333, 'type': 'private'})()
                self.message_id = 777
        
        msg = MockMessage()
        print("Testing process_telegram_message on server...")
        try:
            # Deve falhar no bot.reply_to (400) mas NÃO na criação do AgentAction
            process_telegram_message(app, msg)
            print("Finished (should have failed with 400 but not 500)")
        except Exception as e:
            print(f"Caught expected error: {e}")
            
        # Verificando se o ticket foi criado no Banco de Produção
        action = AgentAction.query.filter_by(title='Crash no Webhook do Telegram').order_by(AgentAction.id.desc()).first()
        if action:
            print(f"✅ Ticket created on PROD: ID {action.id}, Company: {action.company_id}")
        else:
            print("❌ Ticket NOT created on PROD.")

if __name__ == "__main__":
    test_webhook_crash_prevention()
