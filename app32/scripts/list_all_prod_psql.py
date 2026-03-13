
import sys
import os
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
from scripts.deploy.configr_remote_helper import connect_ssh, APP_DIR

def list_all_prod():
    ssh = connect_ssh()
    try:
        cmd = f"cd {APP_DIR} && grep DATABASE_URL .env | cut -d= -f2-"
        stdin, stdout, stderr = ssh.exec_command(cmd)
        db_url = stdout.read().decode().strip()
        
        if db_url:
            sql = "SELECT id, title FROM projects ORDER BY id DESC LIMIT 50;"
            cmd_psql = f"psql \"{db_url}\" -c \"{sql}\""
            stdin, stdout, stderr = ssh.exec_command(cmd_psql)
            print(stdout.read().decode())
    finally:
        ssh.close()

if __name__ == "__main__":
    list_all_prod()
