
import paramiko

HOST = "ip-69-164-205-75.cloudezapp.io"
PORT = 22122
USER = "app2"
PASS = "*Paraiso1978"

PYTHON = "/home/app2/venv/bin/python"
APP_DIR = "/home/app2/public_html/app32"

def upgrade_production():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(HOST, port=PORT, username=USER, password=PASS)
        
        # We need to set FLASK_CONFIG to production
        cmds = [
            f"cd {APP_DIR} && export FLASK_CONFIG=production && {PYTHON} -m flask db upgrade",
            f"touch /home/app2/public_html/restart.txt"
        ]
        
        for cmd in cmds:
            print(f"Executing: {cmd}")
            stdin, stdout, stderr = ssh.exec_command(cmd)
            print(f"STDOUT: {stdout.read().decode()}")
            print(f"STDERR: {stderr.read().decode()}")
            
    finally:
        ssh.close()

if __name__ == "__main__":
    upgrade_production()
