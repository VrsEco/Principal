
import sys
import os
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parents[1]))
from scripts.deploy.configr_remote_helper import connect_ssh, APP_DIR

def grep_env():
    ssh = connect_ssh()
    try:
        stdin, stdout, stderr = ssh.exec_command(f"grep DATABASE_URL {APP_DIR}/.env")
        print("DATABASE_URL:")
        print(stdout.read().decode())
    finally:
        ssh.close()

if __name__ == "__main__":
    grep_env()
