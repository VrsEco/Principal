import paramiko
import os

HOST = "ip-69-164-205-75.cloudezapp.io"
PORT = 22122
USER = "app2"
PASS = "*Paraiso1978"

try:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, port=PORT, username=USER, password=PASS)

    stdin, stdout, stderr = ssh.exec_command("cat /srv/appgestaoversuscombr.45a4cd4b.configr.cloud/www/app32/.env")
    out = stdout.read().decode()
    with open("remote_env.txt", "w") as f:
        f.write(out)
    ssh.close()
except Exception as e:
    with open("remote_env.txt", "w") as f:
        f.write("Error: " + str(e))
