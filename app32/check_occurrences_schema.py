
from database import get_db

pg = get_db()
conn = pg._get_connection()
cursor = conn.cursor()

table = 'occurrences'
print(f"--- Table: {table} ---")
try:
    cursor.execute(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name = '{table}'")
    cols = cursor.fetchall()
    for col in cols:
        print(f"{col[0]}: {col[1]}")
except Exception as e:
    print(f"Error checking {table}: {e}")

conn.close()
