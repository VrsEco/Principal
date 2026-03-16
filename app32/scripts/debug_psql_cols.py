
import sys
import os
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parents[1]))
from scripts.deploy.configr_remote_helper import connect_ssh, APP_DIR

def debug_psql():
    ssh = connect_ssh()
    try:
        cmd = f"cd {APP_DIR} && export $(grep -v '^#' .env | xargs) && psql $DATABASE_URL -c \"SELECT column_name FROM information_schema.columns WHERE table_name = 'incentive_indicators'\""
        stdin, stdout, stderr = ssh.exec_command(cmd)
        print("Search result for 'pol' in indicators:")
        print(stdout.read().decode())
    finally:
        ssh.close()

if __name__ == "__main__":
    debug_psql()
