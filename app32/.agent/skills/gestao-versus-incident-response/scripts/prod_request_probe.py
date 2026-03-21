from __future__ import annotations

import argparse
import json
import shlex
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.deploy.configr_remote_helper import APP_DIR, BASE_DIR, connect_ssh, run_command

PYTHON = f"{BASE_DIR}/.virtualenv/3.12/bin/python"


def main() -> int:
    parser = argparse.ArgumentParser(description='Reproduz request via test_client em produção para investigação de incidentes.')
    parser.add_argument('--method', required=True, help='GET, POST, PUT, PATCH ou DELETE')
    parser.add_argument('--path', required=True, help='Path da aplicação, ex: /api/process-instances/25?company_id=2')
    parser.add_argument('--user-id', type=int, required=True)
    parser.add_argument('--active-company-id', type=int, required=True)
    parser.add_argument('--json-payload', default='{}', help='JSON string do payload')
    parser.add_argument('--env', default='production')
    parser.add_argument('--tail-log', action='store_true')
    args = parser.parse_args()

    method = args.method.upper().strip()
    if method not in {'GET', 'POST', 'PUT', 'PATCH', 'DELETE'}:
        raise SystemExit(f'Método não suportado: {method}')

    try:
        payload_obj = json.loads(args.json_payload)
    except Exception as exc:
        raise SystemExit(f'json-payload inválido: {exc}')

    method_call = {
        'GET': 'get',
        'POST': 'post',
        'PUT': 'put',
        'PATCH': 'patch',
        'DELETE': 'delete',
    }[method]

    remote_script = f"""
import json
from app import create_app
app = create_app({args.env!r})
with app.app_context():
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['_user_id'] = {str(args.user_id)!r}
            sess['_fresh'] = True
            sess['active_company_id'] = {args.active_company_id}
        payload = json.loads({json.dumps(json.dumps(payload_obj))})
        resp = client.{method_call}({args.path!r}, json=payload if {method!r} != 'GET' else None)
        print('STATUS', resp.status_code)
        print('CONTENT_TYPE', resp.headers.get('content-type'))
        body = resp.get_data(as_text=True)
        print(body[:2000])
"""

    command = (
        f"cd {shlex.quote(APP_DIR)} && {shlex.quote(PYTHON)} - <<'PY'\n"
        f"{remote_script}\n"
        "PY"
    )

    ssh = connect_ssh()
    try:
        code, out, err = run_command(ssh, command, get_pty=True)
        print(out)
        if err:
            print('[STDERR]')
            print(err)
        if args.tail_log:
            log_code, log_out, log_err = run_command(ssh, f"tail -n 60 {APP_DIR}/request_debug.log || true")
            print('=== REQUEST_DEBUG_LOG ===')
            print(log_out)
            if log_err:
                print('[LOG STDERR]')
                print(log_err)
        return code
    finally:
        ssh.close()


if __name__ == '__main__':
    raise SystemExit(main())
