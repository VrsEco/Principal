
import sys
import os
sys.path.append(os.getcwd())
import psycopg2
from database.postgresql_db import get_connection

def dump_table(name):
    print(f"\n--- DUMPING TABLE: {name} ---")
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM {name} LIMIT 10")
        colnames = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        print(f"COLUMNS: {colnames}")
        print(f"ROWS ({len(rows)}):")
        for r in rows:
            print(r)
    except Exception as e:
        print(f"ERROR dumping {name}: {e}")
    finally:
        if conn: conn.close()

dump_table("integrations")
dump_table("ai_agents")
dump_table("agent_integrations")
