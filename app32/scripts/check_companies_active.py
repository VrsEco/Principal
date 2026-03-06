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
    cur.execute('SELECT id, name, is_active FROM companies')
    for row in cur.fetchall(): print(row)
    cur.close()
    conn.close()
except Exception as e:
    # Maybe is_active column does not exist
    print('ERROR:', e)
" """
    
    stdin, stdout, stderr = ssh.exec_command(DB_PROBE)
    print(stdout.read().decode())
    
    ssh.close()

if __name__ == "__main__":
    run()
