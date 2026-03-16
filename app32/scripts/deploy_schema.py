
import sys
import os
from pathlib import Path
import base64

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parents[1]))
from scripts.deploy.configr_remote_helper import connect_ssh, APP_DIR

def deploy_schema():
    ssh = connect_ssh()
    try:
        rel_path = "schemas/indicator.py"
        local_path = Path(__file__).parents[1] / rel_path
        with open(local_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        b64_content = base64.b64encode(content.encode()).decode()
        remote_path = f"{APP_DIR}/{rel_path}"
        
        print(f"Deploying {rel_path} to {remote_path}...")
        ssh.exec_command(f"echo '{b64_content}' | base64 -d > {remote_path}")
        print("Schema deployed successfully.")
        
    finally:
        ssh.close()

if __name__ == "__main__":
    deploy_schema()
