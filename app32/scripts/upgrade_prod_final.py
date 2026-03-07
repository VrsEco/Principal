
import paramiko

HOST = "ip-69-164-205-75.cloudezapp.io"
PORT = 22122
USER = "app2"
PASS = "*Paraiso1978"

# CORRECT PATH DISCOVERED:
PYTHON = "/srv/app619.45a4cd4b.configr.cloud/.virtualenv/3.12/bin/python"
APP_DIR = "/home/app2/public_html/app32"

def final_fix():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(HOST, port=PORT, username=USER, password=PASS)
        
        print(f"Applying database upgrade using {PYTHON}...")
        # Set FLASK_APP and FLASK_CONFIG
        cmds = [
            f"cd {APP_DIR} && export FLASK_APP=app.py && export FLASK_CONFIG=production && {PYTHON} -m flask db upgrade",
            f"touch /home/app2/public_html/restart.txt"
        ]
        
        for cmd in cmds:
            print(f"Executing: {cmd}")
            stdin, stdout, stderr = ssh.exec_command(cmd)
            out = stdout.read().decode()
            err = stderr.read().decode()
            if out: print(f"[OUT]: {out}")
            if err: print(f"[ERR]: {err}")
            
        print("Done!")
            
    finally:
        ssh.close()

if __name__ == "__main__":
    final_fix()
