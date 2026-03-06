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
    
    cur.execute('SELECT id, name FROM companies WHERE id = 7')
    row = cur.fetchone()
    print('Company 7:', row)
    
    cur.execute('SELECT count(*) FROM employees WHERE company_id = 7')
    print('Employee count for Co 7:', cur.fetchone()[0])
    
    cur.execute('SELECT id, user_id, name, company_id FROM employees LIMIT 10')
    print('Sample employees:', cur.fetchall())

    cur.close()
    conn.close()
except Exception as e:
    print('ERROR:', e)
" """
    
    stdin, stdout, stderr = ssh.exec_command(DB_PROBE)
    print(stdout.read().decode())
    print("STDERR:", stderr.read().decode())
    
    ssh.close()

if __name__ == "__main__":
    run()
