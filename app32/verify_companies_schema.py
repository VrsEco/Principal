
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()
db_url = os.environ.get('DATABASE_URL').replace('host.docker.internal', 'localhost')

try:
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'companies' ORDER BY ordinal_position")
    cols = [r[0] for r in cur.fetchall()]
    print(f"Total columns: {len(cols)}")
    print(", ".join(cols))
    cur.close()
    conn.close()
except Exception as e:
    print(f"Error: {e}")
