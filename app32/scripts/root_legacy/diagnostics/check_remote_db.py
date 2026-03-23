import paramiko

HOST = "ip-69-164-205-75.cloudezapp.io"
PORT = 22122
USER = "app2"
PASS = "*Paraiso1978"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASS)

stdin, stdout, stderr = ssh.exec_command("psql -U mff2000 -l")
out = stdout.read().decode()
err = stderr.read().decode()

with open("remote_env.txt", "w") as f:
    f.write("STDOUT:\n" + out + "\nSTDERR:\n" + err)

ssh.close()
