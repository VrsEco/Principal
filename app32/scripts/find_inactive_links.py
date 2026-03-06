import paramiko

def run():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect('ip-69-164-205-75.cloudezapp.io', port=22122, username='app2', password='*Paraiso1978')

    # Query to find employees with duplicate names or same user_id in company 5 (since I couldn't find 7)
    DB_PROBE = """python3 -c "
import psycopg2
try:
    conn = psycopg2.connect(dbname='bd_app_versus', user='mff2000', password='*Paraiso1978', host='127.0.0.1')
    cur = conn.cursor()
    
    print('--- Inactive employees with user_id set in ALL companies ---')
    cur.execute('''
        SELECT id, company_id, user_id, name, status 
        FROM employees 
        WHERE status != 'active' AND user_id IS NOT NULL
        LIMIT 20
    ''')
    rows = cur.fetchall()
    for row in rows:
        print(row)
        
    print('\\n--- Employees for user_id 1 ---')
    cur.execute('SELECT id, company_id, user_id, name, status FROM employees WHERE user_id = 1')
    for row in cur.fetchall(): print(row)

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
