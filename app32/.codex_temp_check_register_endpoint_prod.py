from scripts.deploy.configr_remote_helper import connect_ssh, run_command
ssh = connect_ssh()
cmd = '''bash -lc "source '/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/activate' && cd '/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/www/app32' && python - <<'PY'
from app import create_app
app = create_app()
for rule in app.url_map.iter_rules():
    if 'register' in rule.endpoint or '/register' in rule.rule:
        print('RULE::{}::{}'.format(rule.rule, rule.endpoint))
PY"'''
code, out, err = run_command(ssh, cmd)
print('CODE:', code)
if out: print('OUT:\n'+out)
if err: print('ERR:\n'+err)
ssh.close()
