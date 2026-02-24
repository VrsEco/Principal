
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

host = "localhost"
port = "5432"
dbname = os.environ.get("POSTGRES_DB", "bd_app_versus")
user = os.environ.get("POSTGRES_USER", "postgres")
password = os.environ.get("POSTGRES_PASSWORD", "*Paraiso1978")

try:
    conn = psycopg2.connect(host=host, port=port, dbname=dbname, user=user, password=password)
    cur = conn.cursor()
    
    # Listar Tabelas
    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
    tables = [row[0] for row in cur.fetchall()]
    print(f"📊 Tabelas encontradas ({len(tables)}): {', '.join(tables)}")
    
    # Verificar contagem de dados críticos
    critical_tables = ['companies', 'users', 'projects', 'project_tasks', 'employees']
    for table in critical_tables:
        if table in tables:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            count = cur.fetchone()[0]
            print(f"🔹 {table}: {count} registros")
        else:
            print(f"❌ Tabela '{table}' não existe!")

    cur.close()
    conn.close()
except Exception as e:
    print(f"❌ Erro: {e}")
