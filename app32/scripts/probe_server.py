import paramiko

HOST = "ip-69-164-205-75.cloudezapp.io"
PORT = 22122
USER = "app2"
PASS = "*Paraiso1978"

def run_cmd(ssh, cmd):
    print(f"\n--- {cmd} ---")
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    if out: print(out)
    if err: print(f"STDERR: {err}")

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS)

run_cmd(ssh, "ps aux | grep python")
run_cmd(ssh, "ls -la /home/app2/public_html/app32")
run_cmd(ssh, "ls -la /home/app2/public_html")
run_cmd(ssh, "env")

ssh.close()
