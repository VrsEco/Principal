
import psycopg2

def get_cols(table):
    conn = psycopg2.connect(dbname='bd_app31_temp', user='postgres', password='*Paraiso1978', host='localhost')
    cur = conn.cursor()
    cur.execute(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name = '{table}'")
    cols = cur.fetchall()
    print(f"Table: {table}")
    for c in cols:
        print(f"  {c[0]} ({c[1]})")
    cur.close()
    conn.close()

if __name__ == "__main__":
    get_cols('company_projects')
    get_cols('projects')
