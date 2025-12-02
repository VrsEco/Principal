#!/usr/bin/env python3
"""
Script para restaurar dados essenciais do backup
"""
import sys
import os
import re

# Adicionar diretório raiz ao path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, root_dir)

try:
    from config import Config
    from sqlalchemy import create_engine, text, MetaData, Table
    from sqlalchemy.exc import ProgrammingError
    print("✅ Módulos importados com sucesso")
except ImportError as e:
    print(f"❌ Erro ao importar módulos: {e}")
    sys.exit(1)

def get_table_columns(engine, table_name):
    """Obter colunas de uma tabela"""
    try:
        with engine.connect() as conn:
            result = conn.execute(text(f"""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = '{table_name}'
                ORDER BY ordinal_position
            """))
            return [(row[0], row[1], row[2]) for row in result.fetchall()]
    except Exception:
        return []

def create_admin_user(engine):
    """Criar usuário administrador"""
    try:
        from werkzeug.security import generate_password_hash

        with engine.connect() as conn:
            # Verificar se já existe
            result = conn.execute(text("SELECT id FROM users WHERE email = 'versus@gestaoversus.com.br'"))
            if result.fetchone():
                print("✅ Usuário admin já existe")
                return

            # Criar admin
            password_hash = generate_password_hash('abc123')
            conn.execute(text(f"""
                INSERT INTO users (email, password_hash, name, role, is_active, created_at, updated_at)
                VALUES ('versus@gestaoversus.com.br', '{password_hash}', 'Administrador', 'admin', true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """))
            conn.commit()
            print("✅ Usuário admin criado com sucesso")

    except Exception as e:
        print(f"❌ Erro ao criar admin: {e}")

def restore_table_data(engine, table_name, sql_file):
    """Restaurar dados de uma tabela específica"""
    try:
        # Obter estrutura da tabela
        columns = get_table_columns(engine, table_name)
        if not columns:
            print(f"⚠️ Tabela {table_name} não encontrada no banco")
            return 0

        column_names = [col[0] for col in columns]
        print(f"📋 Colunas da tabela {table_name}: {', '.join(column_names)}")

        # Ler arquivo e encontrar INSERTs para esta tabela
        insert_count = 0
        with open(sql_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # Regex para encontrar INSERTs desta tabela
        pattern = rf"INSERT INTO {table_name} \((.*?)\) VALUES (.*?);"
        matches = re.findall(pattern, content, re.IGNORECASE | re.DOTALL)

        if not matches:
            print(f"⚠️ Nenhum INSERT encontrado para tabela {table_name}")
            return 0

        print(f"📊 Encontrados {len(matches)} INSERTs para {table_name}")

        with engine.connect() as conn:
            for columns_str, values_str in matches[:5]:  # Limitar para teste
                try:
                    # Construir comando INSERT
                    insert_sql = f"INSERT INTO {table_name} ({columns_str}) VALUES {values_str}"
                    conn.execute(text(insert_sql))
                    insert_count += 1
                except Exception as e:
                    print(f"❌ Erro no INSERT {insert_count+1}: {str(e)[:50]}...")

            conn.commit()

        print(f"✅ Restaurados {insert_count} registros para {table_name}")
        return insert_count

    except Exception as e:
        print(f"❌ Erro ao restaurar {table_name}: {e}")
        return 0

def main():
    config = Config()
    engine = create_engine(config.SQLALCHEMY_DATABASE_URI, echo=False)

    # Arquivo de backup
    backup_file = r"C:\Users\mff20\Downloads\Cloud_SQL_Export_2025-11-30 (02_47_15).sql"

    if not os.path.exists(backup_file):
        print(f"❌ Arquivo de backup não encontrado: {backup_file}")
        return

    print("🚀 Iniciando restauração de dados essenciais...")
    print(f"📂 Arquivo: {backup_file}")

    # Criar admin primeiro
    create_admin_user(engine)

    # Tabelas essenciais para restaurar (por prioridade)
    essential_tables = [
        'companies',
        'users',
        'employees',
        'projects',
        'plans',
        'indicators',
        'routines',
        'process_instances'
    ]

    total_restored = 0

    for table in essential_tables:
        print(f"\n🔄 Restaurando tabela: {table}")
        restored = restore_table_data(engine, table, backup_file)
        total_restored += restored

    print(f"\n📈 TOTAL RESTAURADO: {total_restored} registros")
    print("🎉 Restauração essencial concluída!")

if __name__ == "__main__":
    main()










