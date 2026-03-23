
import psycopg
DB_URL = "postgresql://app:%2AParaiso1978@localhost:5432/bdversusv2"
try:
    with psycopg.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("CREATE TABLE IF NOT EXISTS test_lg_perm (id int);")
            conn.commit()
            print("Successfully created test table.")
            cur.execute("DROP TABLE test_lg_perm;")
            conn.commit()
            print("Successfully dropped test table.")
except Exception as e:
    print(f"❌ Permission error: {e}")
