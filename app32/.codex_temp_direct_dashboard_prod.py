from scripts.deploy.configr_remote_helper import connect_ssh, run_command
ssh = connect_ssh()
cmd = '''bash -lc "source '/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/activate' && cd '/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/www/app32' && python - <<'PY'
from app import create_app
from flask import session
from api.routes.incentives import dashboard
app = create_app()
with app.app_context():
    with app.test_request_context('/incentives'):
        session['active_company_id'] = 1
        try:
            resp = dashboard.__wrapped__() if hasattr(dashboard, '__wrapped__') else dashboard()
            print('DASHBOARD::OK::{}'.format(type(resp).__name__))
        except Exception as exc:
            import traceback
            print('DASHBOARD::EXC::{}'.format(exc))
            print(traceback.format_exc())
PY"'''
code, out, err = run_command(ssh, cmd)
print('CODE:', code)
if out: print('OUT:\n'+out)
if err: print('ERR:\n'+err)
ssh.close()
