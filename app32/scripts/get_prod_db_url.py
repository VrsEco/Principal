
import sys
import os
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parents[1]))
from scripts.deploy.configr_remote_helper import connect_ssh, APP_DIR

def get_db_url():
    ssh = connect_ssh()
    try:
        remote_file = f"{APP_DIR}/.env"
        stdin, stdout, stderr = ssh.exec_command(f"grep DATABASE_URL {remote_file}")
        content = stdout.read().decode()
        print(content)
    finally:
        ssh.close()

if __name__ == "__main__":
    get_db_url()
