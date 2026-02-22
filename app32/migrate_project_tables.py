
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
    
    # Project Tasks Migration
    print("Checking project_tasks table...")
    add_column_if_not_exists(cur, 'project_tasks', 'employee_id', 'INTEGER')
    add_column_if_not_exists(cur, 'project_tasks', 'score_weight', 'NUMERIC(10, 2) DEFAULT 1.0')
    add_column_if_not_exists(cur, 'project_tasks', 'estimated_hours', 'NUMERIC(10, 2) DEFAULT 0.0')
    add_column_if_not_exists(cur, 'project_tasks', 'worked_hours', 'NUMERIC(10, 2) DEFAULT 0.0')
    add_column_if_not_exists(cur, 'project_tasks', 'completion_date', 'DATE')
    add_column_if_not_exists(cur, 'project_tasks', 'logs', 'JSONB DEFAULT \'[]\'::jsonb')
    add_column_if_not_exists(cur, 'project_tasks', 'stage', 'VARCHAR(50) DEFAULT \'inbox\'')
    add_column_if_not_exists(cur, 'project_tasks', 'priority', 'VARCHAR(20) DEFAULT \'normal\'')
    
    # Projects Migration
    print("Checking projects table...")
    add_column_if_not_exists(cur, 'projects', 'okr_links', 'JSONB')
    add_column_if_not_exists(cur, 'projects', 'kpis', 'JSONB')
    add_column_if_not_exists(cur, 'projects', 'progress', 'INTEGER DEFAULT 0')
    add_column_if_not_exists(cur, 'projects', 'priority', 'VARCHAR(20) DEFAULT \'medium\'')
    add_column_if_not_exists(cur, 'projects', 'portfolio_id', 'INTEGER')
    add_column_if_not_exists(cur, 'projects', 'notes', 'TEXT')
    
    print("Project tables migration completed successfully.")
    
    cur.close()
    conn.close()
except Exception as e:
    print(f"Error during migration: {e}")
