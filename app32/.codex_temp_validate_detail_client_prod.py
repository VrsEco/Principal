from scripts.deploy.configr_remote_helper import connect_ssh, run_command, APP_DIR, BASE_DIR
ssh = connect_ssh()
cmd = '''bash -lc "source '/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/activate' && cd '/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/www/app32' && python - <<'PY'
from app import create_app
from models import User
app = create_app()
paths = [
    ('/processes/1', 9),
    ('/processes/1/book', 9),
    ('/companies/9/process-instances', 9),
    ('/projects/4', 1),
    ('/projects/4/edit', 1),
    ('/meetings/company/1', 1),
    ('/meetings/company/1/meeting/3/report', 1),
    ('/indicators/1', 9),
    ('/indicators/1/edit', 9),
]
with app.app_context():
    user = User.query.order_by(User.id.asc()).first()
    with app.test_client() as client:
        for path, company_id in paths:
            with client.session_transaction() as sess:
                sess['active_company_id'] = company_id
                if user:
                    sess['_user_id'] = str(user.id)
                    sess['_fresh'] = True
            try:
                resp = client.get(path, follow_redirects=False)
                print('DETAIL::{}::{}::{}'.format(path, resp.status_code, resp.headers.get('Location','')))
                if resp.status_code >= 500:
                    print(resp.get_data(as_text=True)[:1200])
            except Exception as exc:
                print('DETAIL::{}::EXC::{}'.format(path, exc))
PY"'''
code, out, err = run_command(ssh, cmd)
print('CODE:', code)
if out: print('OUT:\n'+out)
if err: print('ERR:\n'+err)
ssh.close()
