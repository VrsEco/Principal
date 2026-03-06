import paramiko

def run():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect('ip-69-164-205-75.cloudezapp.io', port=22122, username='app2', password='*Paraiso1978')

    DB_PROBE = """python3 -c "
import psycopg2
def check_db(dbname):
    try:
        conn = psycopg2.connect(dbname=dbname, user='mff2000', password='*Paraiso1978', host='127.0.0.1')
        cur = conn.cursor()
        cur.execute('SELECT id, name FROM companies WHERE id = 7')
        row = cur.fetchone()
        print(f'DB {dbname} - Company 7:', row)
        cur.close()
        conn.close()
    except Exception as e:
        print(f'DB {dbname} ERROR:', e)

check_db('bd_app_versus')
check_db('bd_versusv2')
check_db('bdversusv2')
" """
    
    stdin, stdout, stderr = ssh.exec_command(DB_PROBE)
    print(stdout.read().decode())
    
    ssh.close()

if __name__ == "__main__":
    run()
