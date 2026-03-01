
import os
import sys
from unittest.mock import MagicMock

# Adiciona o caminho do projeto
sys.path.insert(0, os.getcwd())

# Tenta forçar UTF-8 no stdout para evitar erros de emoji no Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from app import create_app
from api.webhooks.telegram_webhook import process_telegram_message

# Mock de Mensagem do Telebot
message = MagicMock()
message.message_id = 999
message.from_user.id = 551989445
message.text = "Ola Sapiens, teste de diagnostico sem emojis"
message.chat.id = 551989445
message.chat.type = "private"

os.environ['TELEGRAM_SETUP_WEBHOOK'] = 'false'
app = create_app('production')

print("Starting simulation...")
try:
    process_telegram_message(app, message)
    print("Simulation finished.")
except Exception as e:
    print(f"CRASH: {str(e)}")
    import traceback
    traceback.print_exc()
