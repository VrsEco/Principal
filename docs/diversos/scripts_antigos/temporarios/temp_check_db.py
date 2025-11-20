import psycopg2

try:
    conn = psycopg2.connect(
        dbname="bd_app_versus_dev",
        user="postgres",
        password="*Paraiso1978",
        host="localhost",
        port=5432,
    )
    cur = conn.cursor()
    cur.execute("SELECT 1")
    print("connected")
    conn.close()
except Exception as e:
    print(type(e).__name__, e)
