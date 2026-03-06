import paramiko
import time

HOST = "ip-69-164-205-75.cloudezapp.io"
PORT = 22122
USER = "app2"
PASS = "*Paraiso1978"

def run_ssh_commands(commands):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(HOST, port=PORT, username=USER, password=PASS)
        for cmd in commands:
            print(f"Executing: {cmd}")
            stdin, stdout, stderr = client.exec_command(cmd)
            out = stdout.read().decode('utf-8', errors='replace')
            err = stderr.read().decode('utf-8', errors='replace')
            if out: print(f"STDOUT: {out}")
            if err: print(f"STDERR: {err}")
    finally:
        client.close()

if __name__ == "__main__":
    # Commands to find python and run migrations
    cmds = [
        "[ -f /home/app2/public_html/app.py ] && echo 'ROOT: /home/app2/public_html' || echo 'NOT IN ROOT'",
        "[ -f /home/app2/public_html/app32/app.py ] && echo 'ROOT: /home/app2/public_html/app32' || echo 'NOT IN app32'",
        "find /home/app2/public_html -name scripts -type d",
        "cd /home/app2/public_html && git log --oneline -1",
        "ls /home/app2/venv/bin/python3"
    ]
    run_ssh_commands(cmds)
