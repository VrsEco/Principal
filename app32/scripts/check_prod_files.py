
import sys
import os
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
from scripts.deploy.configr_remote_helper import connect_ssh, APP_DIR

def check_env():
    ssh = connect_ssh()
    try:
        cmd = f"ls -F {APP_DIR}"
        stdin, stdout, stderr = ssh.exec_command(cmd)
        print(stdout.read().decode())
    finally:
        ssh.close()

if __name__ == "__main__":
    check_env()
