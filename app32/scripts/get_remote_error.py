
import sys
import os
from pathlib import Path
from scripts.deploy.configr_remote_helper import connect_ssh, APP_DIR

def get_error():
    ssh = connect_ssh()
    python_bin = "/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/.virtualenv/3.12/bin/python"
    cmd = f"cd {APP_DIR} && export FLASK_APP=app.py && {python_bin} -c 'from app import create_app; create_app()'"
    stdin, stdout, stderr = ssh.exec_command(cmd)
    print(stderr.read().decode())
    ssh.close()

if __name__ == "__main__":
    get_error()
