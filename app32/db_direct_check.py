import psycopg2
import os
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()

def get_db_params(url):
    result = urlparse(url)
    return {
        "database": result.path[1:],
        "user": result.username,
        "password": result.password,
        "host": "localhost" if result.hostname == "host.docker.internal" else result.hostname,
        "port": result.port or 5432
    }

db_url = os.environ.get("DATABASE_URL")
if not db_url:
    db_url = "postgresql://postgres:*Paraiso1978@localhost:5432/bd_app_versus"

print(f"Connecting to: {db_url}")
params = get_db_params(db_url)
print(f"Connection params: {params}")

try:
    conn = psycopg2.connect(**params)
    cur = conn.cursor()
    
    cur.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'project_tasks'
    """)
    columns = [row[0] for row in cur.fetchall()]
    print(f"Direct columns in project_tasks: {columns}")
    
    if 'logs' not in columns:
        print("Column 'logs' is MISSING in direct check!")
    else:
        print("Column 'logs' is PRESENT in direct check.")
        
    cur.close()
    conn.close()
except Exception as e:
    print(f"Error: {e}")
