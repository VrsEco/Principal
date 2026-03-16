from scripts.deploy.configr_remote_helper import connect_ssh, run_command, APP_DIR, BASE_DIR
ssh = connect_ssh()
cmd = (
    f"bash -lc \"source '{BASE_DIR}/activate' && cd '{APP_DIR}' && python - <<'PY'\n"
    "from app import create_app\n"
    "from models import User\n"
    "app = create_app()\n"
    "with app.app_context():\n"
    "    admin = User.query.filter(User.role.in_(['admin','administrator'])).order_by(User.id.asc()).first()\n"
    "    with app.test_client() as client:\n"
    "        client.post('/login', json={'email': admin.email, 'password': '123456'})\n"
    "        client.post('/portal', json={'company_id': 9})\n"
    "        resp = client.get('/my-work/api/activities?scope=me&active_company_id=9')\n"
    "        data = resp.get_json() or {}\n"
    "        print('STATUS::{}'.format(resp.status_code))\n"
    "        acts = data.get('data') or []\n"
    "        print('COUNT::{}'.format(len(acts)))\n"
    "        for act in acts[:15]:\n"
    "            print('TYPE::{}::ID::{}::INSTANCE::{}::TITLE::{}'.format(act.get('type'), act.get('id'), act.get('instance_id'), act.get('title')))\n"
    "        for act in acts:\n"
    "            if (act.get('type') or '').lower() == 'process':\n"
    "                print('PROCESS_ACTIVITY::{}'.format(act))\n"
    "                break\n"
    "PY\""
)
code, out, err = run_command(ssh, cmd)
print('CODE:', code)
if out: print('OUT:\n' + out)
if err: print('ERR:\n' + err)
ssh.close()
