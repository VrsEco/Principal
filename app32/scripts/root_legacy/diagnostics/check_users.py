
import sys
import os
sys.path.append(os.getcwd())
from database.postgresql_db import get_connection
try:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT email, password, role FROM users LIMIT 5")
    rows = cursor.fetchall()
    for r in rows:
        print(f"EMAIL: {r[0]}, PASS: {r[1]}, ROLE: {r[2]}")
except Exception as e:
    print(f"ERROR: {e}")
