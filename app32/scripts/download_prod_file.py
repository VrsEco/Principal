
import sys
import os
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parents[1]))
from scripts.deploy.configr_remote_helper import connect_ssh, APP_DIR

def download_remote(rel_path, local_dest):
    ssh = connect_ssh()
    try:
        remote_file = f"{APP_DIR}/{rel_path}"
        stdin, stdout, stderr = ssh.exec_command(f"cat {remote_file}")
        content = stdout.read().decode()
        with open(local_dest, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Downloaded {rel_path} to {local_dest}")
    finally:
        ssh.close()

if __name__ == "__main__":
    if len(sys.argv) > 2:
        download_remote(sys.argv[1], sys.argv[2])
    else:
        print("Usage: python download_prod_file.py <relative_path> <local_dest>")
