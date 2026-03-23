
import sys
import os
sys.path.append(os.getcwd())
from database.postgresql_db import get_connection
try:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
    tables = cursor.fetchall()
    print("TABLES:")
    for t in tables:
        print(f"- {t[0]}")
    
    # Check if there is data in any table that looks like integrations
    possible = ['integrations', 'ai_agents', 'agents', 'services']
    for p in possible:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {p}")
            count = cursor.fetchone()[0]
            print(f"TABLE {p} COUNT: {count}")
        except:
            print(f"TABLE {p} does not exist or error")
            conn.rollback()
            cursor = conn.cursor()
            
except Exception as e:
    print(f"ERROR: {e}")
