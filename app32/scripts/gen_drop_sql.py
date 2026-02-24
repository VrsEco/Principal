
import psycopg2
import os

def gen_drop():
    try:
        conn = psycopg2.connect(dbname='bdversusv2', user='postgres', password='*Paraiso1978', host='localhost')
        cur = conn.cursor()
        cur.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
        tables = [r[0] for r in cur.fetchall()]
        with open('backups/drop_tables.sql', 'w') as f:
            for t in tables:
                f.write(f'DROP TABLE IF EXISTS "{t}" CASCADE;\n')
        print(f"Generated drop commands for {len(tables)} tables.")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    gen_drop()
