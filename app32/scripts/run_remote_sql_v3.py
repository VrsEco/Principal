
import sys
import os
from pathlib import Path
import base64

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parents[1]))
from scripts.deploy.configr_remote_helper import connect_ssh, APP_DIR

def run_remote_sql():
    ssh = connect_ssh()
    try:
        local_sql = Path(__file__).parents[1] / "scripts" / "migrate_restructure_v3.sql"
        with open(local_sql, "r", encoding="utf-8") as f:
            content = f.read()
            
        b64_content = base64.b64encode(content.encode()).decode()
        remote_file = f"{APP_DIR}/migrate_restructure_v3.sql"
        
        print(f"Uploading SQL to {remote_file}...")
        ssh.exec_command(f"echo {b64_content} | base64 -d > {remote_file}")
        
        # Run psql using credentials from .env
        # Actually, let's just use the connection string from .env
        cmd = f"cd {APP_DIR} && export $(grep -v '^#' .env | xargs) && psql $DATABASE_URL -f {remote_file}"
        print(f"Running psql on production...")
        stdin, stdout, stderr = ssh.exec_command(cmd)
        
        print("STDOUT:")
        print(stdout.read().decode())
        print("STDERR:")
        print(stderr.read().decode())
        
        ssh.exec_command(f"rm {remote_file}")
        print("Remote sequence finished.")
    finally:
        ssh.close()

if __name__ == "__main__":
    run_remote_sql()
