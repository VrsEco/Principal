import sys
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from scripts.deploy.configr_remote_helper import connect_ssh, APP_DIR

def apply_sql():
    ssh = connect_ssh()
    try:
        sql = "ALTER TABLE meetings ADD COLUMN IF NOT EXISTS planned_duration_minutes INTEGER; ALTER TABLE meetings ADD COLUMN IF NOT EXISTS actual_duration_minutes INTEGER;"
        
        # We'll use a python one-liner on the remote server
        # making sure to escape properly for the remote shell.
        
        remote_cmd = (
            f"cd {APP_DIR} && "
            "export FLASK_CONFIG=production && "
            "/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/.virtualenv/3.12/bin/python -c \"from app import create_app; from models import db; from sqlalchemy import text; app=create_app('production'); "
            "with app.app_context(): db.session.execute(text(\\\"ALTER TABLE meetings ADD COLUMN IF NOT EXISTS planned_duration_minutes INTEGER; ALTER TABLE meetings ADD COLUMN IF NOT EXISTS actual_duration_minutes INTEGER;\\\")); db.session.commit(); print('SQL Applied successfully')\""
        )
        
        print(f"Executing remote command...")
        stdin, stdout, stderr = ssh.exec_command(remote_cmd)
        
        out = stdout.read().decode('utf-8', 'ignore')
        err = stderr.read().decode('utf-8', 'ignore')
        
        print("STDOUT:", out)
        print("STDERR:", err)
        
    finally:
        ssh.close()

if __name__ == "__main__":
    apply_sql()
