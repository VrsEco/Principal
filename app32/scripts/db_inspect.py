import sys
import os
from sqlalchemy import text

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
from app import create_app
from models import db

app = create_app()
with app.app_context():
    print("--- INSPECAO DE TABELA: process_steps ---")
    try:
        res = db.session.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'process_steps'")).fetchall()
        for r in res:
            print(f"Coluna: {r[0]} | Tipo: {r[1]}")
    except Exception as e:
        print(f"Erro: {e}")
