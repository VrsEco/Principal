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

    print("--- CRONTAB ---")
    stdin, stdout, stderr = ssh.exec_command("crontab -l")
    print(stdout.read().decode())
    print(stderr.read().decode())

    print("\n--- SCRIPTS DIR ---")
    stdin, stdout, stderr = ssh.exec_command("ls -la /home/app2/backups")
    print(stdout.read().decode())

    print("\n--- BACKUP SCRIPT CONTENT ---")
    stdin, stdout, stderr = ssh.exec_command("cat /home/app2/backups/backup.sh || true")
    print(stdout.read().decode())
    
    stdin, stdout, stderr = ssh.exec_command("cat /home/app2/backups/push_to_github.sh || true")
    print(stdout.read().decode())

    ssh.close()
except Exception as e:
    print("Error:", e)
