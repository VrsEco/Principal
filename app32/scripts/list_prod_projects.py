
import sys
import os
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
from scripts.deploy.configr_remote_helper import connect_ssh, APP_DIR

def list_prod_projects():
    ssh = connect_ssh()
    try:
        cmd = f"cd {APP_DIR} && python3 -c \"import os, sys; sys.path.append(os.getcwd()); from app import create_app; from models import db, Project; app = create_app(); with app.app_context(): projects = Project.query.all(); [print(f'[{{p.id}}] {{p.name}}') for p in projects]\""
        stdin, stdout, stderr = ssh.exec_command(cmd)
        print(stdout.read().decode())
        print(stderr.read().decode())
    finally:
        ssh.close()

if __name__ == "__main__":
    list_prod_projects()
