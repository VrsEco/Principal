
import sys
import os
sys.path.append(os.getcwd())

from database.postgres_helper import connect as pg_connect
from sqlalchemy import text

def diagnose():
    conn = pg_connect()
    cursor = conn.cursor()
    
    print("Checking tables in 'public' schema:")
    cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
    tables = [row[0] for row in cursor.fetchall()]
    for t in sorted(tables):
        print(f" - {t}")
    
    critical_tables = ['projects', 'project_tasks', 'project_activities', 'company_projects', 'process_instances']
    print("\nChecking critical tables:")
    for t in critical_tables:
        exists = t in tables
        print(f"Table '{t}': {'EXISTS' if exists else 'MISSING'}")
        if exists:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {t}")
                count = cursor.fetchone()[0]
                print(f"   -> count: {count}")
            except Exception as e:
                print(f"   -> ERROR counting: {e}")
                # Reset connection if it failed
                conn = pg_connect()
                cursor = conn.cursor()
    
    conn.close()

if __name__ == "__main__":
    diagnose()
