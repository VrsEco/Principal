import sys
import os
sys.path.append(os.getcwd())
import json
import psycopg2
from database.postgres_helper import PG_USER, PG_HOST, PG_PORT, PG_PASSWORD, PG_DB

def fix_collaborators():
    conn = psycopg2.connect(user=PG_USER, host=PG_HOST, port=PG_PORT, password=PG_PASSWORD, dbname=PG_DB)
    cur = conn.cursor()
    
    # Get all instances with collaborators_json
    cur.execute("SELECT id, collaborators_json FROM process_instances WHERE collaborators_json IS NOT NULL")
    rows = cur.fetchall()
    
    count = 0
    for inst_id, collabs in rows:
        if not collabs or not isinstance(collabs, list):
            continue
            
        # Check if already has entries in process_instance_collaborators
        cur.execute("SELECT count(*) FROM process_instance_collaborators WHERE process_instance_id = %s", (inst_id,))
        if cur.fetchone()[0] > 0:
            continue
            
        print(f"Fixing instance {inst_id}...")
        for c in collabs:
            emp_id = c.get('id') or c.get('employee_id')
            if not emp_id:
                continue
            
            role = c.get('role', 'executor')
            hours = c.get('hours', 0)
            
            cur.execute("""
                INSERT INTO process_instance_collaborators (process_instance_id, employee_id, role, estimated_hours)
                VALUES (%s, %s, %s, %s)
            """, (inst_id, emp_id, role, hours))
            count += 1
            
    conn.commit()
    print(f"Inserted {count} collaborator records.")
    cur.close()
    conn.close()

if __name__ == "__main__":
    fix_collaborators()
