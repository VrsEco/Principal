import paramiko

def run():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect('ip-69-164-205-75.cloudezapp.io', port=22122, username='app2', password='*Paraiso1978')

    DB_PROBE = """python3 -c "
import psycopg2
try:
    conn = psycopg2.connect(dbname='bd_app_versus', user='mff2000', password='*Paraiso1978', host='127.0.0.1')
    cur = conn.cursor()
    
    cur.execute('SELECT id, name FROM companies ORDER BY id')
    rows = cur.fetchall()
    print('All Companies:', rows)
    
    cur.close()
    conn.close()
except Exception as e:
    print('ERROR:', e)
" """
    
    stdin, stdout, stderr = ssh.exec_command(DB_PROBE)
    print(stdout.read().decode())
    
    ssh.close()

if __name__ == "__main__":
    run()
