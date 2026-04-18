from __future__ import annotations

import base64
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.deploy.configr_remote_helper import APP_DIR, connect_ssh


REMOTE_WORKER = r"""
import os
import sys

VENV_SITE = '/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/.virtualenv/3.12/lib/python3.12/site-packages'
if VENV_SITE not in sys.path:
    sys.path.insert(0, VENV_SITE)
if '/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/www/app32' not in sys.path:
    sys.path.insert(0, '/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/www/app32')

os.environ.setdefault('FLASK_ENV', 'production')
os.environ.setdefault('FLASK_CONFIG', 'production')
os.environ.setdefault('OPENAI_API_KEY', 'dummy')
os.environ['APP_BOOTSTRAP_DB_SCHEMA'] = '0'
os.environ['APP_BOOTSTRAP_RUNTIME_SERVICES'] = '0'

try:
    from dotenv import load_dotenv
    load_dotenv('/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/www/app32/.env')
except Exception:
    pass

from src.core.mcp_surface_registry import get_surface_manifest

for surface in ('user', 'admin', 'analytics', 'ops'):
    manifest = get_surface_manifest(surface, include_tools=True)
    summary = manifest.get('summary') or {}
    print(surface, summary.get('capabilities'))
"""


def main() -> int:
    ssh = connect_ssh()
    try:
        remote_file = f"{APP_DIR}/codex_remote_mcp_surface_smoke_worker.py"
        payload = base64.b64encode(REMOTE_WORKER.encode("utf-8")).decode("ascii")
        ssh.exec_command(f"echo {payload} | base64 -d > {remote_file}")
        command = (
            f"cd {APP_DIR} && "
            "/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/.virtualenv/3.12/bin/python "
            f"{remote_file}"
        )
        stdin, stdout, stderr = ssh.exec_command(command, get_pty=True)
        for line in iter(lambda: stdout.readline(2048), ""):
            if not line:
                break
            print(line.rstrip())
        err = stderr.read().decode("utf-8", "ignore").strip()
        code = stdout.channel.recv_exit_status()
        if err:
            print(err)
        ssh.exec_command(f"rm -f {remote_file}")
        return code
    finally:
        ssh.close()


if __name__ == "__main__":
    raise SystemExit(main())
