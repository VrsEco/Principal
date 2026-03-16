from scripts.deploy.configr_remote_helper import connect_ssh, run_command, APP_DIR, BASE_DIR
ssh = connect_ssh()
cmd = (
    f"bash -lc \"source '{BASE_DIR}/activate' && cd '{APP_DIR}' && python - <<'PY'\n"
    "from app import create_app\n"
    "from models import User, Project, ProjectTask, Process, Meeting\n"
    "app = create_app()\n"
    "with app.app_context():\n"
    "    admin = User.query.filter(User.role.in_(['admin','administrator'])).order_by(User.id.asc()).first()\n"
    "    project = Project.query.filter_by(company_id=1).order_by(Project.id.asc()).first()\n"
    "    process = Process.query.filter_by(company_id=1).order_by(Process.id.asc()).first()\n"
    "    task = ProjectTask.query.join(Project, Project.id==ProjectTask.project_id).filter(Project.company_id==1).order_by(ProjectTask.id.asc()).first()\n"
    "    meeting = Meeting.query.filter_by(company_id=1).order_by(Meeting.id.asc()).first()\n"
    "    with app.test_client() as client:\n"
    "        client.post('/login', json={'email': admin.email, 'password': '123456'})\n"
    "        client.post('/portal', json={'company_id': 1})\n"
    "        tests = []\n"
    "        if process:\n"
    "            tests.append(('PROCESS_BOOK_HTML', '/processes/{}/book'.format(process.id)))\n"
    "        if project:\n"
    "            tests.append(('PROJECT_SUMMARY_PDF', '/api/projects/{}/summary-pdf'.format(project.id)))\n"
    "        if task:\n"
    "            tests.append(('TASK_SUMMARY_PDF', '/my-work/api/project-task/{}/summary-pdf'.format(task.id)))\n"
    "        tests.append(('MY_WORK_PRINT_HTML', '/my-work/export-pdf'))\n"
    "        if meeting:\n"
    "            tests.append(('MEETING_REPORT_HTML', '/meetings/company/1/meeting/{}/report'.format(meeting.id)))\n"
    "        for label, path in tests:\n"
    "            resp = client.get(path, follow_redirects=False)\n"
    "            body = resp.get_data() or b''\n"
    "            print('REPORT::{}::STATUS={}::CTYPE={}::SIZE={}'.format(label, resp.status_code, resp.headers.get('Content-Type',''), len(body)))\n"
    "            if resp.status_code < 500 and 'text/html' in (resp.headers.get('Content-Type') or ''):\n"
    "                snippet = body[:220].decode('utf-8','ignore').replace(chr(10),' ').replace(chr(13),' ')\n"
    "                print('HTML_SNIPPET::{}::{}'.format(label, snippet))\n"
    "PY\""
)
code, out, err = run_command(ssh, cmd)
print('CODE:', code)
if out: print('OUT:\n' + out)
if err: print('ERR:\n' + err)
ssh.close()
