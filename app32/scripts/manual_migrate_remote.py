import paramiko

HOST = "ip-69-164-205-75.cloudezapp.io"
PORT = 22122
USER = "app2"
PASS = "*Paraiso1978"

DB_CMD = """python3 -c "
import psycopg2
try:
    conn = psycopg2.connect(dbname='bd_app_versus', user='mff2000', password='*Paraiso1978', host='127.0.0.1')
    cur = conn.cursor()
    cur.execute('CREATE TABLE IF NOT EXISTS user_employee_assignments (id SERIAL PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), employee_id INTEGER NOT NULL REFERENCES employees(id), start_date DATE NOT NULL, end_date DATE, is_active BOOLEAN DEFAULT TRUE, status VARCHAR(20) DEFAULT \\'active\\', notes TEXT, created_at TIMESTAMP NOT NULL DEFAULT NOW(), updated_at TIMESTAMP NOT NULL DEFAULT NOW())')
    cur.execute('ALTER TABLE roles ADD COLUMN IF NOT EXISTS parent_role_id INTEGER REFERENCES roles(id)')
    cur.execute('ALTER TABLE roles ADD COLUMN IF NOT EXISTS weekly_hours NUMERIC(5,2)')
    cur.execute('ALTER TABLE employees ADD COLUMN IF NOT EXISTS weekly_hours NUMERIC(5,2)')
    conn.commit()
    print('MIGRATION COMPLETED SUCCESSFULLY')
    cur.close()
    conn.close()
except Exception as e:
    print('ERROR:', e)
" """

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, port=PORT, username=USER, password=PASS)
    
    print("Executing manual DB migration...")
    stdin, stdout, stderr = ssh.exec_command(DB_CMD)
    print("STDOUT:", stdout.read().decode())
    print("STDERR:", stderr.read().decode())
    
    print("Restarting app...")
    ssh.exec_command("touch /home/app2/public_html/restart.txt")
    ssh.exec_command("touch /home/app2/public_html/app32/passenger_wsgi.py")
    
    ssh.close()

if __name__ == "__main__":
    main()
