import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()
db_url = os.environ.get('DATABASE_URL').replace('host.docker.internal', 'localhost')

conn = psycopg2.connect(db_url)
cur = conn.cursor()

cur.execute("SELECT id, title, company_id FROM projects WHERE company_id = 1;")
projects = cur.fetchall()
print("Projects for company 1:")
for p in projects:
    print(p)
    
print("\nTasks for company 1:")
for p in projects:
    cur.execute(f"SELECT id, project_id, what FROM project_tasks WHERE project_id = {p[0]};")
    tasks = cur.fetchall()
    for t in tasks:
        print(t)
        
cur.close()
conn.close()
