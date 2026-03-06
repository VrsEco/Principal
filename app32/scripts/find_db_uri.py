import paramiko

def run():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect('ip-69-164-205-75.cloudezapp.io', port=22122, username='app2', password='*Paraiso1978')

    cmds = [
        "grep -r 'SQLALCHEMY_DATABASE_URI' /home/app2/public_html/app32/config.py",
        "cat /home/app2/public_html/app32/.env | grep DATABASE",
        "cat /home/app2/public_html/.env | grep DATABASE"
    ]
    
    for cmd in cmds:
        print(f"--- {cmd} ---")
        stdin, stdout, stderr = ssh.exec_command(cmd)
        print(stdout.read().decode('utf-8', errors='ignore'))
        
    ssh.close()

if __name__ == "__main__":
    run()
