from scripts.deploy.configr_remote_helper import connect_ssh, run_command, APP_DIR, BASE_DIR
ssh = connect_ssh()
cmd = '''bash -lc "source '/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/activate' && cd '/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/www/app32' && python - <<'PY'
from app import create_app
from models import User
app = create_app()
tests = [
    ('POST_USER_INVALID', 'POST', '/api/usuarios', 1, {'name': ''}),
    ('PUT_USER_INVALID', 'PUT', '/api/usuarios/1', 1, {'name': ''}),
    ('POST_INC_RULESET_PARTICIPANT_INVALID', 'POST', '/incentives/rules/1/participants', 1, {'employee_id': 0, 'valor_base': 0}),
    ('POST_INC_VETOR_INVALID', 'POST', '/incentives/rules/1/vetores', 1, {'indicator_id': '', 'impact_value': 1}),
    ('PATCH_INC_FACT_INVALID', 'PATCH', '/api/v1/incentives/facts/999999', 1, {'value': 1}),
    ('POST_INC_FACT_VERIFY_INVALID', 'POST', '/api/v1/incentives/facts/999999/verify', 1, None),
    ('POST_AGENT_MENU_INVALID', 'POST', '/api/agents/menu/options', 1, {}),
    ('POST_PROJECT_SUMMARY', 'POST', '/api/projects/4/summary', 1, {}),
    ('POST_PROCESS_UPLOAD_NOFILE', 'POST', '/api/processes/upload-flow', 9, None),
]
with app.app_context():
    user = User.query.order_by(User.id.asc()).first()
    with app.test_client() as client:
        for label, method, path, company_id, payload in tests:
            with client.session_transaction() as sess:
                sess['active_company_id'] = company_id
                if user:
                    sess['_user_id'] = str(user.id)
                    sess['_fresh'] = True
            try:
                if method == 'POST':
                    resp = client.post(path, json=payload) if payload is not None else client.post(path)
                elif method == 'PUT':
                    resp = client.put(path, json=payload)
                elif method == 'PATCH':
                    resp = client.patch(path, json=payload)
                else:
                    raise RuntimeError('unsupported')
                print('WRITE::{}::{}::{}'.format(label, resp.status_code, resp.headers.get('Location','')))
                if resp.status_code >= 500:
                    print(resp.get_data(as_text=True)[:1200])
            except Exception as exc:
                print('WRITE::{}::EXC::{}'.format(label, exc))
PY"'''
code, out, err = run_command(ssh, cmd)
print('CODE:', code)
if out: print('OUT:\n'+out)
if err: print('ERR:\n'+err)
ssh.close()
