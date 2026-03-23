
import subprocess
import os

key_path = "deploy_key_SECRETA.txt"
host = "app@69.164.205.75"
port = "22122"

check_schema_cmd = """
cd /srv/appgestaoversuscombr.45a4cd4b.configr.cloud/www/app32 && \
/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/.virtualenv/3.12/bin/python -c "
import sys, os
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv('.env')
from models import db
from models.agent_action import AgentAction
from app import create_app
app = create_app('production')
with app.app_context():
    from sqlalchemy import inspect
    inst = inspect(db.engine)
    cols = inst.get_columns('agent_actions')
    for c in cols:
        print(f'{c[\'name\']}: {c[\'type\']} (nullable: {c[\'nullable\']})')
"
"""

cmd = [
    "ssh", "-i", key_path, "-p", port, "-o", "StrictHostKeyChecking=no", host,
    f"bash -c \"{check_schema_cmd}\""
]

try:
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    print(result.stdout)
except Exception as e:
    print(f"Error: {e}")
