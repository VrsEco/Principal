"""
Script para listar tabelas do banco de dados
"""
import sys
import os
sys.path.append(os.getcwd())

from app_pev import app
from models import db

with app.app_context():
    print("\n" + "="*80)
    print("📋 TABELAS DO BANCO DE DADOS")
    print("="*80)
    
    # Listar todas as tabelas
    result = db.session.execute(db.text("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        ORDER BY table_name
    """))
    
    tables = [row[0] for row in result]
    
    print(f"\nTotal de tabelas: {len(tables)}\n")
    
    # Filtrar tabelas relacionadas a atividades e processos
    print("Tabelas relacionadas a ATIVIDADES:")
    for table in tables:
        if 'activity' in table.lower() or 'atividade' in table.lower():
            print(f"  - {table}")
    
    print("\nTabelas relacionadas a PROCESSOS:")
    for table in tables:
        if 'process' in table.lower() or 'processo' in table.lower():
            print(f"  - {table}")
    
    print("\nTabelas relacionadas a PROJETOS:")
    for table in tables:
        if 'project' in table.lower() or 'projeto' in table.lower():
            print(f"  - {table}")
    
    print("\n" + "="*80)
    print("✅ Listagem concluída!")
