
import sys
import os
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
from scripts.deploy.configr_remote_helper import connect_ssh, APP_DIR

def find_prod_pid():
    ssh = connect_ssh()
    try:
        # Get DATABASE_URL from .env on server
        cmd = f"cd {APP_DIR} && grep DATABASE_URL .env | cut -d= -f2-"
        stdin, stdout, stderr = ssh.exec_command(cmd)
        db_url = stdout.read().decode().strip()
        print(f"Prod DB URL found: {db_url[:50]}...")
        
        if db_url:
            # Use psql to search for project
            # Configr usually has psql installed.
            # We need to extract parts from db_url or just use the whole URL
            sql = "SELECT id, title FROM projects WHERE title ILIKE '%Agentes%' OR title ILIKE '%AA.J.31%';"
            cmd_psql = f"psql \"{db_url}\" -c \"{sql}\""
            stdin, stdout, stderr = ssh.exec_command(cmd_psql)
            print("PSQL Output:")
            print(stdout.read().decode())
            print(stderr.read().decode())
    finally:
        ssh.close()

if __name__ == "__main__":
    find_prod_pid()
