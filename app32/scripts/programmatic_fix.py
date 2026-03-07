
import paramiko

HOST = "ip-69-164-205-75.cloudezapp.io"
PORT = 22122
USER = "app2"
PASS = "*Paraiso1978"

PYTHON = "/srv/app619.45a4cd4b.configr.cloud/.virtualenv/3.12/bin/python"
APP_DIR = "/home/app2/public_html/app32"

PROGRAMMATIC_MIGRATE = """
import sys, os
sys.path.insert(0, '.')
os.environ.setdefault('FLASK_CONFIG', 'production')
from app import create_app
from flask_migrate import upgrade
app = create_app('production')
with app.app_context():
    print("Starting programatic upgrade...")
    upgrade()
    print("MIGRATION_PROGRAMMATIC_SUCCESS")
"""

def programatic_fix():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(HOST, port=PORT, username=USER, password=PASS)
        
        sftp = ssh.open_sftp()
        with sftp.file("/tmp/run_upgrade.py", "w") as f:
            f.write(PROGRAMMATIC_MIGRATE)
        sftp.close()
        
        cmd = f"cd {APP_DIR} && {PYTHON} /tmp/run_upgrade.py"
        print(f"Executing: {cmd}")
        stdin, stdout, stderr = ssh.exec_command(cmd)
        out = stdout.read().decode()
        err = stderr.read().decode()
        print(f"[OUT]: {out}")
        print(f"[ERR]: {err}")
            
    finally:
        ssh.close()

if __name__ == "__main__":
    programatic_fix()
