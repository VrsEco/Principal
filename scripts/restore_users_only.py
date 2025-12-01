#!/usr/bin/env python3
"""
Restaurar apenas usuários do backup
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
    print("✅ Módulos importados")
except ImportError as e:
    print(f"❌ Erro import: {e}")
    sys.exit(1)

def main():
    config = Config()
    engine = create_engine(config.SQLALCHEMY_DATABASE_URI, echo=False)

    # Arquivo de backup
    backup_file = r"C:\Users\mff20\Downloads\Cloud_SQL_Export_2025-11-30 (02_47_15).sql"

    print("🔄 Lendo backup...")

    try:
        with open(backup_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        print("✅ Arquivo lido")
    except Exception as e:
        print(f"❌ Erro lendo arquivo: {e}")
        return

    # Encontrar INSERTs para users
    pattern = r"INSERT INTO users \((.*?)\) VALUES (.*?);"
    matches = re.findall(pattern, content, re.IGNORECASE | re.DOTALL)

    print(f"📊 Usuários encontrados: {len(matches)}")

    if not matches:
        print("⚠️ Nenhum usuário encontrado no backup")
        # Criar admin manualmente
        create_admin_user(engine)
        return

    with engine.connect() as conn:
        restored = 0
        for columns_str, values_str in matches:
            try:
                insert_sql = f"INSERT INTO users ({columns_str}) VALUES {values_str}"
                conn.execute(text(insert_sql))
                restored += 1
                print(f"✅ Usuário {restored} restaurado")
            except Exception as e:
                print(f"❌ Erro usuário {restored+1}: {str(e)[:50]}...")

        conn.commit()
        print(f"📈 Total usuários restaurados: {restored}")

        # Garantir admin
        create_admin_user(engine)

def create_admin_user(engine):
    """Criar usuário administrador"""
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
            print("✅ Admin criado")

    except Exception as e:
        print(f"❌ Erro admin: {e}")

if __name__ == "__main__":
    main()


