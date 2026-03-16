
import sys
import os
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parents[1]))
from scripts.deploy.configr_remote_helper import connect_ssh, APP_DIR

def read_prod_env():
    ssh = connect_ssh()
    try:
        remote_file = f"{APP_DIR}/.env"
        print(f"Reading {remote_file}...")
        stdin, stdout, stderr = ssh.exec_command(f"cat {remote_file}")
        content = stdout.read().decode()
        print("Content of production .env:")
        print(content)
    finally:
        ssh.close()

if __name__ == "__main__":
    read_prod_env()
