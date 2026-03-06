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
    
    print('--- EMPLOYEES FOR COMPANY 7 ---')
    cur.execute('SELECT id, user_id, name, status FROM employees WHERE company_id = 7')
    rows = cur.fetchall()
    for row in rows:
        print(row)
        
    print('\\n--- RECENT ASSIGNMENTS FOR COMPANY 7 ---')
    cur.execute('''
        SELECT a.id, a.user_id, a.employee_id, a.is_active, a.status, a.end_date 
        FROM user_employee_assignments a
        JOIN employees e ON a.employee_id = e.id
        WHERE e.company_id = 7
        ORDER BY a.created_at DESC
    ''')
    rows = cur.fetchall()
    for row in rows:
        print(row)
        
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
