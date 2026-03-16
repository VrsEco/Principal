from scripts.deploy.configr_remote_helper import connect_ssh, run_command
ssh = connect_ssh()
cmd = '''bash -lc "source '/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/activate' && cd '/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/www/app32' && python - <<'PY'
from app import create_app
from models import User
app = create_app()
with app.app_context():
    user = User.query.order_by(User.id.asc()).first()
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['active_company_id'] = 1
            if user:
                sess['_user_id'] = str(user.id)
                sess['_fresh'] = True
        resp = client.get('/incentives', follow_redirects=False)
        print('INCENTIVES::{}::{}'.format(resp.status_code, resp.headers.get('Location','')))
        if resp.status_code >= 500:
            print(resp.get_data(as_text=True)[:2000])
PY"'''
code, out, err = run_command(ssh, cmd)
print('CODE:', code)
if out: print('OUT:\n'+out)
if err: print('ERR:\n'+err)
ssh.close()
