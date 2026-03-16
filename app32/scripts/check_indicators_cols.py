
import sys
import os
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parents[1]))
from scripts.deploy.configr_remote_helper import connect_ssh, APP_DIR

def check_cols():
    ssh = connect_ssh()
    try:
        cmd = f"cd {APP_DIR} && export $(grep -v '^#' .env | xargs) && psql $DATABASE_URL -c \"\\d indicators\" | head -n 40"
        stdin, stdout, stderr = ssh.exec_command(cmd)
        print(stdout.read().decode())
    finally:
        ssh.close()

if __name__ == "__main__":
    check_cols()
