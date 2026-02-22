from database.postgres_helper import connect
import json

def check_table(table_name):
    conn = connect()
    cursor = conn.cursor()
    cursor.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table_name}'")
    cols = [r[0] for r in cursor.fetchall()]
    print(f"Columns for {table_name}: {cols}")
    conn.close()

if __name__ == "__main__":
    check_table('routines')
    check_table('process_routines')
    check_table('process_steps')
