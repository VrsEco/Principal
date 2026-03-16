
import psycopg2
from urllib.parse import urlparse
import os

def load_env():
    if os.path.exists('.env'):
        with open('.env') as f:
            for line in f:
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value

def inspect_indicators():
    load_env()
    db_url = os.environ.get('DATABASE_URL')
    result = urlparse(db_url)
    conn = psycopg2.connect(
        database=result.path[1:],
        user=result.username,
        password=result.password,
        host=result.hostname,
        port=result.port
    )
    try:
        cur = conn.cursor()
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'indicators'")
        cols = [r[0] for r in cur.fetchall()]
        print(f"Columns in indicators: {cols}")
        cur.close()
    finally:
        conn.close()

if __name__ == "__main__":
    inspect_indicators()
