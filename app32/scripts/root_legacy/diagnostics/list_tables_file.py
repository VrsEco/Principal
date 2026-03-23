import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()
db_url = os.environ.get('DATABASE_URL').replace('host.docker.internal', 'localhost')

with open("tables_utf8.txt", "w", encoding="utf-8") as f:
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
        f.write("Tables in public schema:\n")
        for t in tables:
            f.write(t[0] + "\n")
        
        cur.execute("SELECT count(*) FROM projects;")
        f.write(f"\nCount of projects: {cur.fetchone()[0]}\n")
        
        cur.execute("SELECT count(*) FROM project_tasks;")
        f.write(f"Count of project_tasks: {cur.fetchone()[0]}\n")

        cur.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'projects';
        """)
        f.write("\nProjects columns:\n")
        for col in cur.fetchall():
            f.write(f"  - {col[0]}: {col[1]}\n")

        cur.close()
        conn.close()
    except Exception as e:
        f.write(f"Error: {e}\n")
