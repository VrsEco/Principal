import paramiko

def run():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect('ip-69-164-205-75.cloudezapp.io', port=22122, username='app2', password='*Paraiso1978')

    DB_PROBE = """python3 -c "
import psycopg2
def try_conn(dbname, user, pwd):
    try:
        conn = psycopg2.connect(dbname=dbname, user=user, password=pwd, host='127.0.0.1')
        print(f'SUCCESS: {dbname} as {user}')
        cur = conn.cursor()
        cur.execute('SELECT id, name FROM companies ORDER BY id LIMIT 5')
        print('Companies:', cur.fetchall())
        conn.close()
    except Exception as e:
        print(f'FAILED: {dbname} as {user} - {e}')

try_conn('bdversusv2', 'mff2000', '*Paraiso1978')
try_conn('bd_app_versus', 'mff2000', '*Paraiso1978')
try_conn('bdversusv2', 'postgres', 'password')
" """
    
    stdin, stdout, stderr = ssh.exec_command(DB_PROBE)
    print(stdout.read().decode())
    
    ssh.close()

if __name__ == "__main__":
    run()
