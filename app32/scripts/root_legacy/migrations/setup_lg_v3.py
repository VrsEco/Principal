
import psycopg
from langgraph.checkpoint.postgres import PostgresSaver

DB_URL = "postgresql://app:%2AParaiso1978@localhost:5432/bdversusv2"

print("Direct connection setup...")
try:
    with psycopg.connect(DB_URL) as conn:
        # Check current search path or schema
        with conn.cursor() as cur:
            cur.execute("SELECT current_schema();")
            print(f"Current schema: {cur.fetchone()}")
            
        saver = PostgresSaver(conn)
        print("Running saver.setup()...")
        saver.setup()
        print("✅ Success!")
except Exception as e:
    print(f"❌ Failed: {e}")
    import traceback
    traceback.print_exc()
