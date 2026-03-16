
import sys
import os
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parents[1]))
from scripts.deploy.configr_remote_helper import connect_ssh, APP_DIR

def read_log():
    ssh = connect_ssh()
    try:
        stdin, stdout, stderr = ssh.exec_command(f"cat {APP_DIR}/test_app_init_output.txt")
        print(stdout.read().decode())
    finally:
        ssh.close()

if __name__ == "__main__":
    read_log()
