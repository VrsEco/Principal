
import psycopg
DB_URL = "postgresql://app:%2AParaiso1978@localhost:5432/bdversusv2"
with psycopg.connect(DB_URL) as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_name LIKE 'checkpoint%'")
        print(f"Tables found: {cur.fetchall()}")
