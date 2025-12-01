#!/usr/bin/env python3
"""
Analisar conteúdo do backup para identificar tabelas e dados
"""
import sys
import os
import re

# Adicionar diretório raiz ao path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, root_dir)

from config import Config
from sqlalchemy import create_engine, text

def main():
    backup_file = r"C:\Users\mff20\Downloads\Cloud_SQL_Export_2025-11-30 (02_47_15).sql"

    if not os.path.exists(backup_file):
        print(f"❌ Arquivo não encontrado: {backup_file}")
        return

    print("🔍 ANALISANDO CONTEÚDO DO BACKUP...")
    print(f"📂 Arquivo: {backup_file}")
    print()

    # Ler backup
    with open(backup_file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    # Encontrar todos os comandos COPY (incluindo schema public.)
    copy_pattern = r'COPY (?:public\.)?(\w+)\s*\((.*?)\)\s*FROM stdin;'
    copy_matches = re.findall(copy_pattern, content, re.IGNORECASE | re.DOTALL)

    print(f"📊 Total de tabelas no backup: {len(copy_matches)}")
    print()

    # Verificar tabelas no banco atual
    config = Config()
    engine = create_engine(config.SQLALCHEMY_DATABASE_URI, echo=False)

    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public'
        """))
        current_tables = {row[0] for row in result.fetchall()}

    print("🔄 COMPARAÇÃO TABELA POR TABELA:")
    print("=" * 60)

    tables_to_import = []
    tables_missing = []

    for table_name, columns_str in copy_matches:
        exists_in_current = table_name in current_tables

        # Contar linhas de dados
        copy_block_pattern = rf'COPY {table_name}.*?FROM stdin;(.*?)\\.'
        block_match = re.search(copy_block_pattern, content, re.IGNORECASE | re.DOTALL)

        data_lines = 0
        if block_match:
            data_lines = len([line for line in block_match.group(1).strip().split('\n') if line.strip()])

        columns = [col.strip() for col in columns_str.split(',')]

        status = "✅ EXISTE" if exists_in_current else "❌ FALTA"
        print("2d")

        if exists_in_current:
            tables_to_import.append((table_name, data_lines, columns))

    print()
    print("🎯 TABELAS QUE PODEM SER IMPORTADAS:")
    print("=" * 60)

    for table_name, data_lines, columns in tables_to_import:
        print("2d")

    print()
    print(f"📊 RESUMO:")
    print(f"   ✅ Tabelas compatíveis: {len(tables_to_import)}")
    print(f"   ❌ Tabelas faltando: {len(copy_matches) - len(tables_to_import)}")
    print(f"   📦 Total de registros no backup: ~{sum(data[1] for data in tables_to_import)}")

if __name__ == "__main__":
    main()
