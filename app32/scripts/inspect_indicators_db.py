
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

def inspect_db():
    load_env()
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        print("DATABASE_URL not found")
        return

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
        
        tables = ['indicators', 'incentive_indicators', 'indicator_groups', 'incentive_indicator_tree']
        for table in tables:
            cur.execute(f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{table}')")
            exists = cur.fetchone()[0]
            if not exists:
                print(f"\n--- Table {table} does not exist ---")
                continue

            print(f"\n--- Columns in {table} ---")
            cur.execute(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name = '{table}' ORDER BY ordinal_position")
            rows = cur.fetchall()
            for row in rows:
                print(f"{row[0]}: {row[1]}")
                
        cur.close()
    finally:
        conn.close()

if __name__ == "__main__":
    inspect_db()
