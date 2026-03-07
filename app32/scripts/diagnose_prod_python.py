
import paramiko

HOST = "ip-69-164-205-75.cloudezapp.io"
PORT = 22122
USER = "app2"
PASS = "*Paraiso1978"

# We'll try both possible paths discovered
PATHS = [
    "/srv/app619.45a4cd4b.configr.cloud/.virtualenv/3.12/bin/python",
    "/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/.virtualenv/3.12/bin/python",
    "python3.12",
    "python3",
    "python"
]

def check_env():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(HOST, port=PORT, username=USER, password=PASS)
        
        for p in PATHS:
            print(f"--- Checking path: {p} ---")
            cmd = f"{p} -c \"import flask; print('Flask version:', flask.__version__)\""
            stdin, stdout, stderr = ssh.exec_command(cmd)
            out = stdout.read().decode().strip()
            err = stderr.read().decode().strip()
            if out: print(f"  [OUT]: {out}")
            if err: print(f"  [ERR]: {err}")
            
    finally:
        ssh.close()

if __name__ == "__main__":
    check_env()
