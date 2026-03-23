import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()
db_url = os.environ.get('DATABASE_URL').replace('host.docker.internal', 'localhost')

with open("company_projects_count.txt", "w", encoding="utf-8") as f:
    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        
        for table in ['company_projects', 'project_activities', 'plan_alignment_project']:
            cur.execute(f"SELECT count(*) FROM {table};")
            f.write(f"Count of {table}: {cur.fetchone()[0]}\n")

        cur.close()
        conn.close()
    except Exception as e:
        f.write(f"Error: {e}\n")
