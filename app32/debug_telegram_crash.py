
import os
import sys
from unittest.mock import MagicMock

# Adiciona o caminho do projeto
sys.path.insert(0, os.getcwd())

from app import create_app
from api.webhooks.telegram_webhook import process_telegram_message

# Mock de Mensagem do Telebot
message = MagicMock()
message.from_user.id = 551989445  # Um ID real ou fictício que esteja no banco
message.text = "Olá Sapiens, teste de diagnóstico"
message.chat.id = 551989445

os.environ['TELEGRAM_SETUP_WEBHOOK'] = 'false'
app = create_app('production')

print("🚀 Iniciando simulação de mensagem do Telegram...")
process_telegram_message(app, message)
print("🏁 Simulação concluída. Verifique os logs acima se houve erro.")
