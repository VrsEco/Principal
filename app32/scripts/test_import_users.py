#!/usr/bin/env python3
"""
Teste: importar apenas usuários do backup
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
    print("🧪 TESTE: Importação de usuários")
    print()

    backup_file = r"C:\Users\mff20\Downloads\Cloud_SQL_Export_2025-11-30 (02_47_15).sql"

    if not os.path.exists(backup_file):
        print(f"❌ Arquivo não encontrado: {backup_file}")
        return

    # Ler backup
    with open(backup_file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    # Extrair dados de usuários
    columns, data_lines = extract_copy_data(content, 'users')

    if not columns or not data_lines:
        print("❌ Nenhum dado de usuário encontrado")
        return

    print(f"📋 Colunas encontradas: {columns}")
    print(f"👥 Usuários no backup: {len(data_lines)}")

    # Mostrar primeiros 3 usuários
    print("\n👀 Primeiros usuários do backup:")
    for i, line in enumerate(data_lines[:3]):
        values = line.split('\t')
        if len(values) >= 4:  # id, email, name, password
            user_id = values[0]
            email = values[1] if len(values) > 1 else "?"
            name = values[2] if len(values) > 2 else "?"
            print(f"  {i+1}. ID:{user_id} | {email} | {name}")

    # Conectar ao banco
    config = Config()
    engine = create_engine(config.SQLALCHEMY_DATABASE_URI, echo=False)

    # Verificar usuários atuais
    with engine.connect() as conn:
        result = conn.execute(text("SELECT id, email, name FROM users LIMIT 5"))
        current_users = result.fetchall()

    print(f"\n👤 Usuários atuais no banco: {len(current_users)}")
    for user in current_users:
        print(f"  ID:{user[0]} | {user[1]} | {user[2]}")

    print("\n❓ Deseja continuar com a importação completa?")
    print("💡 Este teste mostra que podemos importar dados seletivamente")

def extract_copy_data(content, table_name):
    """Extrair dados de um bloco COPY específico"""
    copy_pattern = rf'COPY (?:public\.)?{table_name}\s*\((.*?)\)\s*FROM stdin;(.*?)(?=COPY|\Z)'
    match = re.search(copy_pattern, content, re.IGNORECASE | re.DOTALL)

    if not match:
        return None, []

    columns_str, data_block = match.groups()
    columns = [col.strip() for col in columns_str.split(',')]

    data_lines = []
    for line in data_block.split('\n'):
        line = line.strip()
        if line == '\\.' or not line:
            break
        if line:
            data_lines.append(line)

    return columns, data_lines

if __name__ == "__main__":
    main()














