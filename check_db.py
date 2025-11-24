
import sys
import os

# Adicionar o diretório atual ao path para importar app
sys.path.append(os.getcwd())

from app_pev import app
from models import db
from sqlalchemy import inspect
from models.note import Note

with app.app_context():
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    print(f"Tabelas existentes: {tables}")
    
    if 'notes' in tables:
        print("Tabela 'notes' ENCONTRADA.")
        # Verificar colunas
        columns = [c['name'] for c in inspector.get_columns('notes')]
        print(f"Colunas na tabela 'notes': {columns}")
    else:
        print("Tabela 'notes' NÃO ENCONTRADA.")
        print("Tentando criar tabela 'notes'...")
        try:
            # Tenta criar apenas as tabelas que faltam
            db.create_all()
            print("db.create_all() executado com sucesso.")
        except Exception as e:
            print(f"Erro ao criar tabelas: {e}")
