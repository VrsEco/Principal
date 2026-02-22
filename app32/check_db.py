import psycopg2
import sys
import os
from dotenv import load_dotenv

load_dotenv()
db_url = os.environ.get('DATABASE_URL').replace('host.docker.internal', 'localhost')

conn = psycopg2.connect(db_url)
cur = conn.cursor()

try:
    cur.execute("SELECT id, title FROM projects ORDER BY id LIMIT 10")
    print("First 10 projects:")
    for r in cur.fetchall():
        print(r)
        
    cur.execute("SELECT id, project_id, what FROM project_tasks ORDER BY id LIMIT 10")
    print("First 10 tasks:")
    for r in cur.fetchall():
        print(r)

    print("\nSpecific projects:")
    cur.execute("SELECT id, title FROM projects WHERE id IN (1, 99999, 90001)")
    for r in cur.fetchall():
        print(r)

    print("\nSpecific tasks:")
    cur.execute("SELECT id, project_id, what FROM project_tasks WHERE project_id IN (1, 99999, 90001)")
    for r in cur.fetchall():
        print(r)
        
except Exception as e:
    print(e)
finally:
    cur.close()
    conn.close()
