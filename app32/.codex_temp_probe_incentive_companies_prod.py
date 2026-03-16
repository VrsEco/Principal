from scripts.deploy.configr_remote_helper import connect_ssh, run_command, APP_DIR, BASE_DIR
ssh = connect_ssh()
cmd = (
    f"bash -lc \"source '{BASE_DIR}/activate' && cd '{APP_DIR}' && python - <<'PY'\n"
    "from app import create_app\n"
    "from sqlalchemy import text\n"
    "app = create_app()\n"
    "with app.app_context():\n"
    "    from models import db\n"
    "    queries = {\n"
    "        'rulesets': 'SELECT company_id, COUNT(*) FROM incentive_rule_sets GROUP BY company_id ORDER BY COUNT(*) DESC',\n"
    "        'participants': 'SELECT company_id, COUNT(*) FROM incentive_participants GROUP BY company_id ORDER BY COUNT(*) DESC',\n"
    "        'rules': 'SELECT company_id, COUNT(*) FROM incentive_rules GROUP BY company_id ORDER BY COUNT(*) DESC',\n"
    "        'calcs': 'SELECT company_id, COUNT(*) FROM incentive_calculations GROUP BY company_id ORDER BY COUNT(*) DESC',\n"
    "    }\n"
    "    for label, sql in queries.items():\n"
    "        rows = db.session.execute(text(sql)).fetchall()\n"
    "        print(label.upper() + '::' + str(rows[:10]))\n"
    "PY\""
)
code, out, err = run_command(ssh, cmd)
print('CODE:', code)
if out: print('OUT:\n'+out)
if err: print('ERR:\n'+err)
ssh.close()
