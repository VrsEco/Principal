from database.postgres_helper import connect
conn = connect()
cur = conn.cursor()
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'routines'")
print(",".join([r[0] for r in cur.fetchall()]))
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'process_routines'")
print(",".join([r[0] for r in cur.fetchall()]))
conn.close()
