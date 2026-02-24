import sys
import os

# Add app32 to sys.path
sys.path.insert(0, '/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/www/app32')

from app import db, create_app

try:
    print("Iniciando reset do banco de dados em produção...")
    app = create_app('production')
    with app.app_context():
        print("Removendo tabelas existentes...")
        db.drop_all()
        print("Criando novas tabelas...")
        db.create_all()
        print("Banco resetado com sucesso.")
except Exception as e:
    import traceback
    traceback.print_exc()
    sys.exit(1)
