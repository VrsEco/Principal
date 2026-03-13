import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()
url = os.getenv('DATABASE_URL')
conn = psycopg2.connect(url)
cur = conn.cursor()
cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name LIKE 'incentive_%'")
tables = cur.fetchall()
print(f"Encontradas {len(tables)} tabelas:")
for t in tables:
    print(f" - {t[0]}")
cur.close()
conn.close()
