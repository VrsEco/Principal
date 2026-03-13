
import sys
import os
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
from scripts.deploy.configr_remote_helper import connect_ssh, APP_DIR

def list_prod():
    ssh = connect_ssh()
    try:
        # Create a temp script on the server
        remote_script_path = f"{APP_DIR}/tmp_list_projects.py"
        script_content = """
import os, sys
sys.path.append(os.getcwd())
from app import create_app
from models import db, Project

app = create_app()
with app.app_context():
    projects = Project.query.all()
    for p in projects:
        print(f"[{p.id}] {p.name}")
"""
        # Uploading via kitty or cat
        stdin, stdout, stderr = ssh.exec_command(f"cat > {remote_script_path} << 'EOF'\n{script_content}\nEOF")
        
        # Run it
        cmd = f"cd {APP_DIR} && python3 tmp_list_projects.py"
        stdin, stdout, stderr = ssh.exec_command(cmd)
        print(stdout.read().decode())
        
        # Cleanup
        ssh.exec_command(f"rm {remote_script_path}")
    finally:
        ssh.close()

if __name__ == "__main__":
    list_prod()
