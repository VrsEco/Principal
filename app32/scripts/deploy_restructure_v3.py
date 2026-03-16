
import sys
import os
from pathlib import Path
import base64

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parents[1]))
from scripts.deploy.configr_remote_helper import connect_ssh, APP_DIR

FILES_TO_DEPLOY = [
    "models/indicator.py",
    "models/incentive.py",
    "models/__init__.py",
    "schemas/indicator.py",
    "api/resources/indicator.py",
    "api/resources/incentive.py",
    "api/routes/indicators.py",
    "api/routes/incentives.py",
    "api/routes/processes.py",
    "services/incentive_service.py",
    "app.py"
]

def deploy():
    ssh = connect_ssh()
    try:
        for rel_path in FILES_TO_DEPLOY:
            local_path = Path(__file__).parents[1] / rel_path
            if not local_path.exists():
                print(f"Skipping {rel_path} (not found locally)")
                continue
                
            print(f"Deploying {rel_path}...")
            with open(local_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            b64_content = base64.b64encode(content.encode()).decode()
            remote_path = f"{APP_DIR}/{rel_path}"
            
            # Ensure dir exists
            remote_dir = os.path.dirname(remote_path)
            ssh.exec_command(f"mkdir -p {remote_dir}")
            
            # Write file
            ssh.exec_command(f"echo {b64_content} | base64 -d > {remote_path}")
            
        print("All files deployed. Restarting app (touching app.py)...")
        ssh.exec_command(f"touch {APP_DIR}/app.py")
        
        print("Testing app initialization...")
        python_bin = "/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/.virtualenv/3.12/bin/python"
        cmd = f"cd {APP_DIR} && export FLASK_APP=app.py && {python_bin} -c 'from app import create_app; create_app()'"
        stdin, stdout, stderr = ssh.exec_command(cmd)
        
        err = stderr.read().decode()
        if err:
            print("INITIALIZATION ERROR:")
            print(err)
        else:
            print("App initialized successfully on production!")
            
    finally:
        ssh.close()

if __name__ == "__main__":
    deploy()
