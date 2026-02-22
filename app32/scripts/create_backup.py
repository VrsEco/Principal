"""
Script para criar backup do banco de dados atual antes da recuperação
"""
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus
import json
from datetime import datetime
import os

password = quote_plus("*Paraiso1978")
url = f"postgresql://postgres:{password}@localhost:5432/bd_app_versus"
engine = create_engine(url)

# Criar diretório de backups se não existir
backup_dir = r"C:\GestaoVersus\app31\backups"
os.makedirs(backup_dir, exist_ok=True)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup_file = os.path.join(backup_dir, f"backup_schema_{timestamp}.sql")

print(f"Criando backup em: {backup_file}")

with engine.connect() as conn:
    # Pegar schema de todas as tabelas
    with open(backup_file, 'w', encoding='utf-8') as f:
        f.write(f"-- Backup do schema do banco bd_app_versus\n")
        f.write(f"-- Data: {datetime.now()}\n\n")
        
        # Listar todas as tabelas
        result = conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema='public' 
            AND table_type='BASE TABLE'
            ORDER BY table_name
        """))
        
        tables = [row[0] for row in result]
        f.write(f"-- Tabelas no banco: {', '.join(tables)}\n\n")
        
        # Para cada tabela, pegar o CREATE TABLE
        for table in tables:
            if table == 'alembic_version':
                continue
                
            f.write(f"\n-- Tabela: {table}\n")
            
            # Contar registros
            count_result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
            count = count_result.scalar()
            f.write(f"-- Registros: {count}\n")
            
            # Pegar colunas
            cols_result = conn.execute(text(f"""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name = '{table}'
                ORDER BY ordinal_position
            """))
            
            f.write(f"-- Colunas:\n")
            for col in cols_result:
                f.write(f"--   {col[0]}: {col[1]} {'NULL' if col[2]=='YES' else 'NOT NULL'} {f'DEFAULT {col[3]}' if col[3] else ''}\n")

print(f"✓ Backup do schema criado com sucesso!")
print(f"  Arquivo: {backup_file}")
print(f"  Tabelas: {len(tables)}")
