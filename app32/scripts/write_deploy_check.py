
import paramiko

def write_check():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect("ip-69-164-205-75.cloudezapp.io", port=22122, username="app", password="*Paraiso1978")
    
    cmd = "echo 'EliteSquad-v2026-03-07' > /srv/appgestaoversuscombr.45a4cd4b.configr.cloud/www/app32/static/deploy_check.txt"
    ssh.exec_command(cmd)
    ssh.close()

if __name__ == "__main__":
    write_check()
