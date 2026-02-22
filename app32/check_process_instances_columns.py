
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()
db_url = os.environ.get('DATABASE_URL').replace('host.docker.internal', 'localhost')

try:
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    
    cur.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'process_instances'
        ORDER BY ordinal_position;
    """)
    
    columns = cur.fetchall()
    print("Columns in 'process_instances' table:")
    for col in columns:
        print(f" - {col[0]} ({col[1]})")
    
    cur.close()
    conn.close()
except Exception as e:
    print(f"Error: {e}")
