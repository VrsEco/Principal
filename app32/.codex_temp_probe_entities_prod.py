from scripts.deploy.configr_remote_helper import connect_ssh, run_command, APP_DIR, BASE_DIR
ssh = connect_ssh()
cmd = f'''bash -lc "source '{BASE_DIR}/activate' && cd '{APP_DIR}' && python - <<'PY'
from app import create_app
from models import db
from sqlalchemy import text
app = create_app()
queries = [
    ('process', 'SELECT id, company_id FROM processes ORDER BY id ASC LIMIT 5'),
    ('project', 'SELECT id, company_id FROM projects ORDER BY id ASC LIMIT 5'),
    ('meeting', 'SELECT id, company_id FROM meetings ORDER BY id ASC LIMIT 5'),
    ('indicator', 'SELECT id, company_id FROM indicators ORDER BY id ASC LIMIT 5'),
]
with app.app_context():
    for label, sql in queries:
        try:
            rows = db.session.execute(text(sql)).fetchall()
            print(label.upper() + '::' + str(rows))
        except Exception as exc:
            print(label.upper() + '::EXC::' + str(exc))
PY"'''
code, out, err = run_command(ssh, cmd)
print('CODE:', code)
if out: print('OUT:\n'+out)
if err: print('ERR:\n'+err)
ssh.close()
