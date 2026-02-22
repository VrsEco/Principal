import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()
db_url = os.environ.get('DATABASE_URL').replace('host.docker.internal', 'localhost')

with open("company_projects_schema.txt", "w", encoding="utf-8") as f:
    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        
        for table in ['company_projects', 'project_activities']:
            cur.execute(f"""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = '{table}';
            """)
            f.write(f"\nSchema of {table}:\n")
            for col in cur.fetchall():
                f.write(f"  - {col[0]}: {col[1]}\n")

        cur.close()
        conn.close()
    except Exception as e:
        f.write(f"Error: {e}\n")
