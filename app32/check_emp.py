from database.postgres_helper import connect
conn = connect()
cur = conn.cursor()
cur.execute("SELECT id, name, status, user_id, company_id FROM employees WHERE id = 71;")
row = cur.fetchone()
print(f"EMPLOYEE 71: {row}")
conn.close()
