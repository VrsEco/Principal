
import paramiko

HOST = "ip-69-164-205-75.cloudezapp.io"
PORT = 22122
USER = "app2"
PASS = "*Paraiso1978"

# Path confirmed by official deploy script in Step 877
PYTHON_PATH = "/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/.virtualenv/3.12/bin/python"
APP_DIR = "/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/www/app32"

def verify_and_fix():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(HOST, port=PORT, username=USER, password=PASS)
        
        print("🔍 Verifying current migration head...")
        cmd = f"cd {APP_DIR} && {PYTHON_PATH} -m flask db current"
        stdin, stdout, stderr = ssh.exec_command(cmd)
        print(f"STDOUT: {stdout.read().decode()}")
        print(f"STDERR: {stderr.read().decode()}")
        
        # If the migration is not applied, apply it
        print("🚀 Applying database upgrade...")
        cmd = f"cd {APP_DIR} && {PYTHON_PATH} -m flask db upgrade"
        stdin, stdout, stderr = ssh.exec_command(cmd)
        print(f"STDOUT: {stdout.read().decode()}")
        print(f"STDERR: {stderr.read().decode()}")
        
    finally:
        ssh.close()

if __name__ == "__main__":
    verify_and_fix()
