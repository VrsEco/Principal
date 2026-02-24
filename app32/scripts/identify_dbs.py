
import psycopg2

def list_tables(db_name):
    try:
        conn = psycopg2.connect(
            dbname=db_name,
            user='postgres',
            password='*Paraiso1978',
            host='localhost',
            port='5432'
        )
        cur = conn.cursor()
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
        tables = [t[0] for t in cur.fetchall()]
        print(f"Database: {db_name}")
        print(f"Tables: {len(tables)}")
        # print(tables)
        cur.close()
        conn.close()
        return tables
    except Exception as e:
        print(f"Error connecting to {db_name}: {e}")
        return []

if __name__ == "__main__":
    dbs = ['bd_gestao_versus', 'bd_app_versus', 'bd_app31_temp', 'bdversusv2']
    for db in dbs:
        list_tables(db)
