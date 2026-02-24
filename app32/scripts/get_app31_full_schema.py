
import psycopg2

def get_tables_info():
    conn = psycopg2.connect(dbname='bd_app31_temp', user='postgres', password='*Paraiso1978', host='localhost')
    cur = conn.cursor()
    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
    tables = [t[0] for t in cur.fetchall()]
    
    with open('scripts/app31_schema_full.txt', 'w', encoding='utf-8') as f:
        for table in sorted(tables):
            f.write(f"\nTable: {table}\n")
            cur.execute(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name = '{table}'")
            cols = cur.fetchall()
            for c in cols:
                f.write(f"  {c[0]} ({c[1]})\n")
    cur.close()
    conn.close()
    print("Full APP31 schema saved to scripts/app31_schema_full.txt")

if __name__ == "__main__":
    get_tables_info()
