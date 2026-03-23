
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

# Use localhost instead of host.docker.internal if running locally on Windows
db_url = os.environ.get('DATABASE_URL').replace('host.docker.internal', 'localhost')

try:
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    
    cur.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'companies'
        ORDER BY ordinal_position;
    """)
    
    columns = cur.fetchall()
    print("--- START COLUMNS ---")
    for col in columns:
        print(f"{col[0]}|{col[1]}")
    print("--- END COLUMNS ---")
    
    cur.close()
    conn.close()
except Exception as e:
    print(f"Error: {e}")
