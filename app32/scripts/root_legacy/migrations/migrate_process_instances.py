
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()
db_url = os.environ.get('DATABASE_URL').replace('host.docker.internal', 'localhost')

def add_column_if_not_exists(cur, table, column, data_type):
    cur.execute(f"""
        SELECT count(*) 
        FROM information_schema.columns 
        WHERE table_name = '{table}' AND column_name = '{column}';
    """)
    if cur.fetchone()[0] == 0:
        print(f"Adding column {column} to {table}...")
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {data_type};")
    else:
        print(f"Column {column} already exists in {table}.")

try:
    conn = psycopg2.connect(db_url)
    conn.autocommit = True
    cur = conn.cursor()
    
    # Process Instances Migration
    add_column_if_not_exists(cur, 'process_instances', 'actual_end_date', 'DATE')
    add_column_if_not_exists(cur, 'process_instances', 'score_weight', 'NUMERIC(10, 2) DEFAULT 1.0')
    add_column_if_not_exists(cur, 'process_instances', 'collaborators_json', 'JSONB')
    add_column_if_not_exists(cur, 'process_instances', 'instance_code', 'VARCHAR(100)')
    
    # Check if we need to migrate assigned_collaborators to collaborators_json
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'process_instances' AND column_name = 'assigned_collaborators';")
    if cur.fetchone():
        print("Migrating data from assigned_collaborators to collaborators_json...")
        cur.execute("UPDATE process_instances SET collaborators_json = assigned_collaborators::jsonb WHERE collaborators_json IS NULL AND assigned_collaborators IS NOT NULL;")
        
    print("Migration of process_instances completed successfully.")
    
    cur.close()
    conn.close()
except Exception as e:
    print(f"Error during migration: {e}")
