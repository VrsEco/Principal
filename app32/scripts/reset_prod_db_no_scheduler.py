import sys
import os

sys.path.insert(0, '/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/www/app32')

from app import db, create_app

print("Iniciando reset do banco de dados em produção (sem scheduler)...")
app = create_app('production')

# Disable scheduler locally for the script
app.config['SCHEDULER_API_ENABLED'] = False

with app.app_context():
    print("Removendo tabelas existentes...")
    try:
        db.drop_all()
        print("Tabelas removidas.")
    except Exception as e:
        print(f"Erro ao remover: {e}")
        
    print("Criando novas tabelas...")
    try:
        db.create_all()
        print("Banco resetado com sucesso.")
    except Exception as e:
        print(f"Erro ao criar: {e}")

# Try forcefully exiting so we don't hang due to any scheduler threads
import os
os._exit(0)
