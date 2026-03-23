import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()
db_url = os.environ.get('DATABASE_URL').replace('host.docker.internal', 'localhost')

try:
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    cur.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        ORDER BY table_name;
    """)
    tables = cur.fetchall()
    print("Tables in public schema:")
    for t in tables:
        print(t[0])
    
    cur.execute("SELECT count(*) FROM projects;")
    print(f"Count of projects: {cur.fetchone()[0]}")
    
    cur.execute("SELECT count(*) FROM project_tasks;")
    print(f"Count of project_tasks: {cur.fetchone()[0]}")

    # Check columns of projects
    cur.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'projects';
    """)
    print("Projects columns:")
    for col in cur.fetchall():
        print(f"  - {col[0]}: {col[1]}")

    cur.close()
    conn.close()
except Exception as e:
    print(f"Error: {e}")
