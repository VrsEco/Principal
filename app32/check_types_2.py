from database.postgres_helper import connect
conn = connect()
cur = conn.cursor()
cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'routines' AND column_name = 'is_active'")
print(list(cur.fetchone()))
cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'process_routines' AND column_name = 'is_active'")
print(list(cur.fetchone()))
conn.close()
