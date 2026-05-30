from __future__ import annotations

import base64
import json
from pathlib import Path
from urllib.parse import urlparse

from app32.tests.e2e.config.environments import E2EEnvironmentSettings, E2EExecutionMode


def _supports_remote_bootstrap(settings: E2EEnvironmentSettings) -> bool:
    if settings.execution_mode is not E2EExecutionMode.PROD_SAFE:
        return False
    hostname = urlparse(settings.base_url).hostname or ""
    return hostname.endswith("gestaoversus.com.br")


def _remote_script(settings: E2EEnvironmentSettings) -> str:
    return f"""
import json
from app import create_app

app = create_app('production')
with app.test_client() as client:
    login_response = client.post('/login', json={{
        'email': {settings.username!r},
        'password': {settings.password!r},
        'next': {settings.post_login_path!r},
    }})
    payload = login_response.get_json(silent=True) or {{}}
    if login_response.status_code != 200 or not payload.get('success'):
        raise SystemExit(json.dumps({{'ok': False, 'stage': 'login', 'status': login_response.status_code, 'payload': payload}}))

    if {settings.company_id!r} is not None:
        portal_response = client.post('/portal', json={{'company_id': {settings.company_id!r}}})
        portal_payload = portal_response.get_json(silent=True) or {{}}
        if portal_response.status_code != 200 or not portal_payload.get('success'):
            raise SystemExit(json.dumps({{'ok': False, 'stage': 'portal', 'status': portal_response.status_code, 'payload': portal_payload}}))

    cookie = client.get_cookie('gv_session')
    if cookie is None or not getattr(cookie, 'value', None):
        raise SystemExit(json.dumps({{'ok': False, 'stage': 'cookie', 'status': 500, 'payload': 'missing gv_session'}}))

    print(json.dumps({{'ok': True, 'cookie_name': 'gv_session', 'cookie_value': cookie.value}}))
"""


def bootstrap_remote_prod_safe_storage_state(settings: E2EEnvironmentSettings) -> Path | None:
    if not _supports_remote_bootstrap(settings):
        return None

    from app32.scripts.deploy.configr_remote_helper import APP_DIR, connect_ssh, run_command

    encoded = base64.b64encode(_remote_script(settings).encode("utf-8")).decode("ascii")
    command = (
        f"cd {APP_DIR} && "
        "/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/.virtualenv/3.12/bin/python "
        f"-c \"import base64; exec(base64.b64decode('{encoded}').decode('utf-8'))\""
    )

    ssh = connect_ssh()
    try:
        code, out, err = run_command(ssh, command)
    finally:
        ssh.close()

    output = (out or "").strip().splitlines()
    if code != 0 or not output:
        raise RuntimeError(f"Falha no bootstrap remoto PROD_SAFE: {err or out or code}")

    payload = json.loads(output[-1])
    if not payload.get("ok"):
        raise RuntimeError(f"Bootstrap remoto PROD_SAFE inválido: {payload}")

    hostname = urlparse(settings.base_url).hostname or ""
    storage_payload = {
        "cookies": [
            {
                "name": payload["cookie_name"],
                "value": payload["cookie_value"],
                "domain": hostname,
                "path": "/",
                "httpOnly": True,
                "secure": True,
                "sameSite": "Lax",
            }
        ],
        "origins": [],
    }
    settings.storage_state_path.parent.mkdir(parents=True, exist_ok=True)
    settings.storage_state_path.write_text(
        json.dumps(storage_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return settings.storage_state_path
