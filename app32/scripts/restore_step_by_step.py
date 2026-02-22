#!/usr/bin/env python3
"""
Restauração passo a passo do backup
"""
import sys
import os
import re

# Adicionar diretório raiz ao path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, root_dir)

try:
    from config import Config
    from sqlalchemy import create_engine, text
    from werkzeug.security import generate_password_hash
    print("✅ Módulos OK")
except ImportError as e:
    print(f"❌ Erro módulos: {e}")
    sys.exit(1)

def create_admin():
    """Criar admin se não existir"""
    print("👤 Verificando/criando admin...")
    config = Config()
    engine = create_engine(config.SQLALCHEMY_DATABASE_URI, echo=False)

    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT id FROM users WHERE email = 'versus@gestaoversus.com.br'"))
            if result.fetchone():
                print("✅ Admin já existe")
                return

            password_hash = generate_password_hash('abc123')
            conn.execute(text(f"""
                INSERT INTO users (email, password_hash, name, role, is_active, created_at, updated_at)
                VALUES ('versus@gestaoversus.com.br', '{password_hash}', 'Administrador', 'admin', true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """))
            conn.commit()
            print("✅ Admin criado: versus@gestaoversus.com.br / abc123")

    except Exception as e:
        print(f"❌ Erro admin: {e}")

def restore_table(table_name, backup_file):
    """Restaurar uma tabela específica"""
    print(f"🔄 Restaurando {table_name}...")

    config = Config()
    engine = create_engine(config.SQLALCHEMY_DATABASE_URI, echo=False)

    try:
        with open(backup_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except Exception as e:
        print(f"❌ Erro lendo backup: {e}")
        return 0

    # Encontrar INSERTs para esta tabela
    pattern = rf"INSERT INTO {table_name} \((.*?)\) VALUES (.*?);"
    matches = re.findall(pattern, content, re.IGNORECASE | re.DOTALL)

    if not matches:
        print(f"⚠️ Nenhum dado encontrado para {table_name}")
        return 0

    print(f"📊 {len(matches)} registros encontrados")

    restored = 0
    with engine.connect() as conn:
        for columns_str, values_str in matches[:10]:  # Limitar para teste
            try:
                insert_sql = f"INSERT INTO {table_name} ({columns_str}) VALUES {values_str}"
                conn.execute(text(insert_sql))
                restored += 1
            except Exception as e:
                if "duplicate key" not in str(e).lower():
                    print(f"❌ Erro insert: {str(e)[:50]}...")

        conn.commit()

    print(f"✅ {restored} registros restaurados para {table_name}")
    return restored

def main():
    backup_file = r"C:\Users\mff20\Downloads\Cloud_SQL_Export_2025-11-30 (02_47_15).sql"

    if not os.path.exists(backup_file):
        print(f"❌ Backup não encontrado: {backup_file}")
        return

    print("🚀 Iniciando restauração passo a passo...")
    print(f"📂 Backup: {backup_file}")

    # Passo 1: Criar admin
    create_admin()

    # Passo 2: Restaurar tabelas essenciais
    tables_to_restore = ['companies', 'users', 'employees', 'projects']

    total_restored = 0
    for table in tables_to_restore:
        restored = restore_table(table, backup_file)
        total_restored += restored

    print(f"\n📈 TOTAL RESTAURADO: {total_restored} registros")
    print("🎉 Restauração concluída!")

if __name__ == "__main__":
    main()














