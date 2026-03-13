import sys
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from scripts.deploy.configr_remote_helper import connect_ssh, APP_DIR

def apply_sql_robust():
    ssh = connect_ssh()
    try:
        script_content = """
from app import create_app
from models import db
from sqlalchemy import text
import sys

try:
    app = create_app('production')
    with app.app_context():
        # Add columns if not exist
        db.session.execute(text('ALTER TABLE meetings ADD COLUMN IF NOT EXISTS planned_duration_minutes INTEGER;'))
        db.session.execute(text('ALTER TABLE meetings ADD COLUMN IF NOT EXISTS actual_duration_minutes INTEGER;'))
        db.session.commit()
        print('DATABASE MIGRATED SUCCESSFULLY')
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
"""
        # Create remote file using cat
        # Need to escape $ if any, but there aren't any here.
        remote_file = f"{APP_DIR}/tmp_fix_db_v2.py"
        
        # Use a more reliable way to write the file
        stdin, stdout, stderr = ssh.exec_command(f"cat > {remote_file}")
        stdin.write(script_content)
        stdin.channel.shutdown_write()
        
        print(f"Executing remote script {remote_file}...")
        py_path = "/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/.virtualenv/3.12/bin/python"
        remote_cmd = f"export FLASK_CONFIG=production && {py_path} {remote_file}"
        
        stdin, stdout, stderr = ssh.exec_command(remote_cmd)
        
        print("STDOUT:", stdout.read().decode('utf-8', 'ignore'))
        print("STDERR:", stderr.read().decode('utf-8', 'ignore'))
        
        # Cleanup
        ssh.exec_command(f"rm {remote_file}")
        
    finally:
        ssh.close()

if __name__ == "__main__":
    apply_sql_robust()
