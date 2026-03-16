from scripts.deploy.configr_remote_helper import connect_ssh, run_command, APP_DIR, BASE_DIR
ssh = connect_ssh()
cmd = (
    f"bash -lc \"source '{BASE_DIR}/activate' && cd '{APP_DIR}' && python - <<'PY'\n"
    "from app import create_app\n"
    "from models import Meeting, Company\n"
    "app = create_app()\n"
    "with app.app_context():\n"
    "    meetings = Meeting.query.order_by(Meeting.company_id.asc(), Meeting.id.asc()).limit(20).all()\n"
    "    for m in meetings:\n"
    "        print('MEETING::id={}::company={}::status={}::project_id={}::title={}'.format(m.id, m.company_id, m.status, m.project_id, (m.title or '')[:60]))\n"
    "PY\""
)
code, out, err = run_command(ssh, cmd)
print('CODE:', code)
if out: print('OUT:\n' + out)
if err: print('ERR:\n' + err)
ssh.close()
