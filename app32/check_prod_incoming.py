
import subprocess
import os

key_path = "deploy_key_SECRETA.txt"
host = "app@69.164.205.75"
port = "22122"

# 1. Verificar mensagens recentes (AgentMessage)
# 2. Verificar novos tickets de erro (AgentAction)
# 3. Verificar o arquivo de log de emergência que criamos no Webhook
remote_cmd = """
cd /srv/appgestaoversuscombr.45a4cd4b.configr.cloud/www/app32 && \
/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/.virtualenv/3.12/bin/python -c "
import sys, os
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv('.env')
from app import create_app
from models import db, AgentMessage, AgentAction
app = create_app('production')
with app.app_context():
    print('--- MENSAGENS RECENTES (PROD) ---')
    msgs = AgentMessage.query.order_by(AgentMessage.id.desc()).limit(3).all()
    for m in msgs:
        print(f'ID: {m.id} | Canal: {m.channel} | Criado em: {m.created_at} | Conteudo: {m.content[:50]}')
    
    print('\\n--- TICKETS DE ERRO (PROD) ---')
    actions = AgentAction.query.order_by(AgentAction.id.desc()).limit(3).all()
    for a in actions:
        print(f'Ticket #{a.id} | Status: {a.status} | Titulo: {a.title} | Criado em: {a.created_at}')
"
echo -e "\n--- LOG DE EMERGÊNCIA (request_debug.log) ---"
tail -n 20 /srv/appgestaoversuscombr.45a4cd4b.configr.cloud/www/app32/request_debug.log
"""

cmd = [
    "ssh", "-i", key_path, "-p", port, "-o", "StrictHostKeyChecking=no", host,
    f"bash -c \"{remote_cmd}\""
]

print("Verificando se a mensagem chegou no servidor de produção...")
try:
    with open("prod_check_output.txt", "wb") as f_out:
        result = subprocess.run(cmd, stdout=f_out, stderr=subprocess.STDOUT, timeout=60)
    
    # Lendo com latin-1 para evitar erros de encoding no terminal
    with open("prod_check_output.txt", "r", encoding='latin-1', errors='replace') as f:
        print(f.read())
except Exception as e:
    print(f"Erro ao verificar: {e}")
