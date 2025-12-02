#!/usr/bin/env python3
"""
Testar conexão com o banco de dados
"""
import sys
import os

# Adicionar diretório raiz ao path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, root_dir)

try:
    from config import Config
    from sqlalchemy import create_engine, text
    print("✅ Importações OK")
except ImportError as e:
    print(f"❌ Erro de importação: {e}")
    sys.exit(1)

def main():
    try:
        config = Config()
        print(f"🔗 Conectando a: {config.SQLALCHEMY_DATABASE_URI.split('@')[1] if '@' in config.SQLALCHEMY_DATABASE_URI else 'banco'}")

        engine = create_engine(config.SQLALCHEMY_DATABASE_URI, echo=False)

        with engine.connect() as conn:
            # Testar conexão
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"✅ Conectado! PostgreSQL: {version[:50]}...")

            # Contar tabelas
            result = conn.execute(text("""
                SELECT COUNT(*) FROM information_schema.tables
                WHERE table_schema = 'public'
            """))
            table_count = result.fetchone()[0]
            print(f"📊 Tabelas no banco: {table_count}")

            # Verificar usuário admin
            result = conn.execute(text("SELECT COUNT(*) FROM users WHERE email = 'versus@gestaoversus.com.br'"))
            admin_count = result.fetchone()[0]
            print(f"👤 Usuários admin: {admin_count}")

            # Listar algumas tabelas
            result = conn.execute(text("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
                LIMIT 10
            """))
            tables = [row[0] for row in result.fetchall()]
            print(f"📋 Primeiras tabelas: {', '.join(tables)}")

    except Exception as e:
        print(f"❌ Erro de conexão: {e}")

if __name__ == "__main__":
    main()










