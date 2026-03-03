
import os
import traceback
from psycopg_pool import ConnectionPool
from langgraph.checkpoint.postgres import PostgresSaver

DB_URL = "postgresql://app:%2AParaiso1978@localhost:5432/bdversusv2"

def setup():
    try:
        # Use pool to ensure it's handled properly
        with ConnectionPool(conninfo=DB_URL, max_size=2, min_size=1) as pool:
            with pool.connection() as conn:
                print("Successfully connected to the database via Pool.")
                saver = PostgresSaver(conn)
                print("Configuring tables...")
                try:
                    saver.setup()
                    print("✅ LangGraph tables are ready.")
                except Exception as e:
                    print(f"❌ Error during saver.setup(): {e}")
                    traceback.print_exc()
    except Exception as e:
        print(f"❌ Connection error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    setup()
