from scripts.deploy.configr_remote_helper import connect_ssh, run_command, APP_DIR, BASE_DIR
ssh = connect_ssh()
validate_cmd = (
    f"bash -lc \"source '{BASE_DIR}/activate' && cd '{APP_DIR}' && python - <<'PY'\n"
    "from app import create_app\n"
    "from flask import session\n"
    "from api.resources.incentive import IncentiveSpiderWebResource\n"
    "import traceback\n"
    "app = create_app()\n"
    "with app.app_context():\n"
    "    with app.test_request_context('/api/incentives/spider-web-data'):\n"
    "        session['active_company_id'] = 1\n"
    "        try:\n"
    "            data = IncentiveSpiderWebResource().get()\n"
    "            print('SPIDER::OK::{}'.format(len(data.get('nodes', [])) if isinstance(data, dict) else type(data).__name__))\n"
    "        except Exception as exc:\n"
    "            print('SPIDER::EXC::{}'.format(exc))\n"
    "            print(traceback.format_exc())\n"
    "PY\""
)
code, out, err = run_command(ssh, validate_cmd)
print('CODE:', code)
if out:
    print('OUT:\n' + out)
if err:
    print('ERR:\n' + err.encode('utf-8', 'ignore').decode('utf-8', 'ignore'))
ssh.close()
