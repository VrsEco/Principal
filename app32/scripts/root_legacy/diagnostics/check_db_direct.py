
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

host = "localhost" # Force localhost for host running
port = "5432"
dbname = os.environ.get("POSTGRES_DB", "bd_app_versus")
user = os.environ.get("POSTGRES_USER", "postgres")
password = os.environ.get("POSTGRES_PASSWORD", "*Paraiso1978")

print(f"Tentando conectar ao banco {dbname} em {host}:{port} como {user}...")

try:
    conn = psycopg2.connect(
        host=host,
        port=port,
        dbname=dbname,
        user=user,
        password=password,
        connect_timeout=5
    )
    print("✅ Conexão psycopg2 bem-sucedida!")
    
    cur = conn.cursor()
    cur.execute("SELECT version();")
    print(f"Versão do PostgreSQL: {cur.fetchone()[0]}")
    
    cur.execute("SELECT current_database();")
    print(f"Banco atual: {cur.fetchone()[0]}")
    
    cur.close()
    conn.close()
    print("✅ Teste finalizado com sucesso.")
except Exception as e:
    print(f"❌ Erro na conexão: {e}")
