
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
    with open('tables_list.txt', 'w') as f:
        for table in tables:
            f.write(f"{table}\n")
    print("Tables written to tables_list.txt")
    
    if 'project_tasks' in tables:
        columns = [c['name'] for c in inspector.get_columns('project_tasks')]
        with open('project_tasks_columns.txt', 'w') as f:
            f.write(str(columns))
        print("Columns written to project_tasks_columns.txt")
    else:
        print("Tabela 'notes' NÃO ENCONTRADA.")
        print("Tentando criar tabela 'notes'...")
        try:
            # Tenta criar apenas as tabelas que faltam
            db.create_all()
            print("db.create_all() executado com sucesso.")
        except Exception as e:
            print(f"Erro ao criar tabelas: {e}")
