import sys
from pathlib import Path
import os

# Add local project root to path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from scripts.deploy.configr_remote_helper import connect_ssh

def get_remote_logs():
    ssh = connect_ssh()
    try:
        log_path = '/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/log/uwsgi/uwsgi.log'
        cmd = f"grep -A 50 'Traceback' {log_path} | tail -n 100"
        stdin, stdout, stderr = ssh.exec_command(cmd)
        print("--- REMOTE LOGS (TRACEBACK) ---")
        print(stdout.read().decode('utf-8', 'ignore'))
        
        # If no traceback found recently, just get last lines
        cmd = f"tail -n 100 {log_path}"
        stdin, stdout, stderr = ssh.exec_command(cmd)
        print("--- LAST 100 LINES ---")
        print(stdout.read().decode('utf-8', 'ignore'))
        
    finally:
        ssh.close()

if __name__ == "__main__":
    get_remote_logs()
