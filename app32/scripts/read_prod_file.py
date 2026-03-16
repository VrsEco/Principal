
import sys
import os
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parents[1]))
from scripts.deploy.configr_remote_helper import connect_ssh, APP_DIR

def read_remote(rel_path):
    ssh = connect_ssh()
    try:
        remote_file = f"{APP_DIR}/{rel_path}"
        stdin, stdout, stderr = ssh.exec_command(f"cat {remote_file}")
        content = stdout.read().decode()
        print(content)
    finally:
        ssh.close()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        read_remote(sys.argv[1])
    else:
        print("Usage: python read_prod_file.py <relative_path>")
