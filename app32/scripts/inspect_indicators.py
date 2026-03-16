import sys
import os
from sqlalchemy import text

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
from app import create_app
from models import db

app = create_app()
with app.app_context():
    print("\n--- INSPECAO DE TABELA: indicators ---")
    res = db.session.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'indicators'")).fetchall()
    for r in res:
        print(f"Coluna: {r[0]} | Tipo: {r[1]}")
        
    print("--- INSPECAO DE TABELA: indicator_data ---")
    try:
        res = db.session.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'indicator_data'")).fetchall()
        for r in res:
            print(f"Coluna: {r[0]} | Tipo: {r[1]}")
            
        print("\n--- INSPECAO DE TABELA: indicator_goals ---")
        res = db.session.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'indicator_goals'")).fetchall()
        for r in res:
            print(f"Coluna: {r[0]} | Tipo: {r[1]}")
            
        print(f"Linhas em indicator_data: {db.session.execute(text('SELECT count(*) FROM indicator_data')).scalar()}")
        res = db.session.execute(text('SELECT * FROM indicator_data')).fetchall()
        for r in res:
            print(f"Dados indicator_data: {dict(r._mapping)}")
            
        print(f"Linhas em indicator_goals: {db.session.execute(text('SELECT count(*) FROM indicator_goals')).scalar()}")
        res = db.session.execute(text('SELECT * FROM indicator_goals')).fetchall()
        for r in res:
            print(f"Dados indicator_goals: {dict(r._mapping)}")
            
    except Exception as e:
        print(f"Erro: {e}")
