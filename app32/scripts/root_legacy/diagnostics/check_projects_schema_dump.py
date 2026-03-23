import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from database.postgres_helper import connect as pg_connect

try:
    conn = pg_connect()
    c = conn.cursor()
    c.execute("SELECT table_name FROM information_schema.tables WHERE table_name LIKE '%project%';")
    print("TABLES:", c.fetchall())

    c.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'projects';")
    print("PROJECTS COLS:", c.fetchall())

    c.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'project_tasks';")
    print("PROJECT_TASKS COLS:", c.fetchall())
except Exception as e:
    print(e)
