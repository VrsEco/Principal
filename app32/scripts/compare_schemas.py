import sys
import os
from pathlib import Path
import psycopg2

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import connect from helper for Cloud (uses Connector)
from database.postgres_helper import connect as connect_helper

def get_tables(connection, label):
    try:
        cur = connection.cursor()
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name
        """)
        tables = {row[0] for row in cur.fetchall()}
        print(f"✅ {label}: {len(tables)} tabelas encontradas.")
        return tables
    except Exception as e:
        print(f"❌ {label}: Erro ao listar tabelas: {e}")
        return set()

def main():
    print("=" * 60)
    print("COMPARATIVO DE TABELAS: LOCAL vs CLOUD")
    print("=" * 60)

    # 1. CLOUD (Via Helper/Connector)
    print("\n☁️  Conectando ao CLOUD...")
    # Ensure env var is set for helper
    os.environ["CLOUD_SQL_CONNECTION_NAME"] = "vrs-eco-478714:southamerica-east1:gestaoversus-db-prod"
    try:
        conn_cloud = connect_helper()
        tables_cloud = get_tables(conn_cloud, "CLOUD")
    except Exception as e:
        print(f"❌ Erro fatal conectando ao Cloud: {e}")
        tables_cloud = set()

    # 2. LOCAL (Via psycopg2 direto)
    print("\n💻 Conectando ao LOCAL...")
    # Try standard local port
    local_dsn = "postgresql://postgres:*Paraiso1978@localhost:5432/bd_app_versus"
    try:
        conn_local = psycopg2.connect(local_dsn)
        tables_local = get_tables(conn_local, "LOCAL")
        
        # Verify if it's really local by checking for a known local-only table
        if 'ui_pages' in tables_local and 'ui_pages' not in tables_cloud:
            print("   (Confirmado: Parece ser o banco Local)")
        elif 'ui_pages' not in tables_local and 'ui_catalog' in tables_local:
            print("   ⚠️  AVISO: O banco conectado em localhost:5432 parece ser o CLOUD (via Proxy?)")
            print("      Tentando porta 5433...")
            try:
                local_dsn_alt = "postgresql://postgres:*Paraiso1978@localhost:5433/bd_app_versus"
                conn_local_alt = psycopg2.connect(local_dsn_alt)
                tables_local_alt = get_tables(conn_local_alt, "LOCAL (5433)")
                tables_local = tables_local_alt
                conn_local = conn_local_alt
            except:
                print("      Falha na porta 5433 também.")

    except Exception as e:
        print(f"❌ Erro conectando ao Local: {e}")
        tables_local = set()

    # 3. Comparação
    print("\n" + "-" * 60)
    print("RELATÓRIO DE DIVERGÊNCIAS")
    print("-" * 60)

    only_local = tables_local - tables_cloud
    only_cloud = tables_cloud - tables_local
    common = tables_local & tables_cloud

    if only_local:
        print(f"\n📍 Apenas no LOCAL ({len(only_local)}):")
        for t in sorted(only_local):
            print(f"   - {t}")
    else:
        print("\n📍 Nenhum tabela exclusiva do Local.")

    if only_cloud:
        print(f"\n☁️  Apenas no CLOUD ({len(only_cloud)}):")
        for t in sorted(only_cloud):
            print(f"   - {t}")
    else:
        print("\n☁️  Nenhuma tabela exclusiva do Cloud.")

    print(f"\n🔗 Tabelas em comum: {len(common)}")

if __name__ == "__main__":
    main()
