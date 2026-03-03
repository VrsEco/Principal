
import psycopg
from langgraph.checkpoint.postgres import PostgresSaver

DB_URL = "postgresql://app:%2AParaiso1978@localhost:5432/bdversusv2"

print("Direct connection setup (AUTOCOMMIT=TRUE)...")
try:
    with psycopg.connect(DB_URL, autocommit=True) as conn:
        saver = PostgresSaver(conn)
        print("Running saver.setup()...")
        saver.setup()
        print("✅ Success!")
except Exception as e:
    print(f"❌ Failed: {e}")
    import traceback
    traceback.print_exc()
