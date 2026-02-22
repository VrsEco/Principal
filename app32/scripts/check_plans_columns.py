
import sys
sys.path.insert(0, '.')
from app import app
with app.app_context():
    from database.postgres_helper import connect as pg_connect
    conn = pg_connect()
    c = conn.cursor()
    c.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'plans' ORDER BY ordinal_position")
    try:
        columns = [r[0] for r in c.fetchall()]
        print('Columns in plans table:', columns)
    except Exception as e:
        print(e)
    conn.close()
