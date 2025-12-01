"""
Script para dropar e recriar o banco de dados bd_app_versus
"""
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus
import sys

password = quote_plus("*Paraiso1978")

# Conectar ao banco postgres (não ao bd_app_versus)
admin_url = f"postgresql://postgres:{password}@localhost:5432/postgres"
engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")

print("Conectando ao PostgreSQL...")

with engine.connect() as conn:
    print("\n1. Encerrando conexões ativas ao bd_app_versus...")
    try:
        conn.execute(text("""
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = 'bd_app_versus'
              AND pid <> pg_backend_pid()
        """))
        print("   ✓ Conexões encerradas")
    except Exception as e:
        print(f"   ⚠ Aviso ao encerrar conexões: {e}")
    
    print("\n2. Dropando banco bd_app_versus...")
    try:
        conn.execute(text("DROP DATABASE IF EXISTS bd_app_versus"))
        print("   ✓ Banco dropado")
    except Exception as e:
        print(f"   ✗ Erro ao dropar banco: {e}")
        sys.exit(1)
    
    print("\n3. Criando novo banco bd_app_versus...")
    try:
        conn.execute(text("""
            CREATE DATABASE bd_app_versus
            WITH OWNER = postgres
            ENCODING = 'UTF8'
            LC_COLLATE = 'Portuguese_Brazil.1252'
            LC_CTYPE = 'Portuguese_Brazil.1252'
            TEMPLATE = template0
        """))
        print("   ✓ Banco criado")
    except Exception as e:
        print(f"   ✗ Erro ao criar banco: {e}")
        sys.exit(1)

print("\n✅ Banco bd_app_versus recriado com sucesso!")
print("\nPróximo passo: Restaurar o backup")
