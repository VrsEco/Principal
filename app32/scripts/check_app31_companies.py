
import psycopg2

def check_companies():
    conn = psycopg2.connect(dbname='bd_app31_temp', user='postgres', password='*Paraiso1978', host='localhost')
    cur = conn.cursor()
    cur.execute('SELECT id, name, client_code FROM companies ORDER BY client_code')
    rows = cur.fetchall()
    print("Empresas encontradas no APP31:")
    for r in rows:
        print(f"Code: {r[2]} | ID: {r[0]} | Name: {r[1]}")
    cur.close()
    conn.close()

if __name__ == "__main__":
    check_companies()
