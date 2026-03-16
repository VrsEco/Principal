from scripts.deploy.configr_remote_helper import connect_ssh, run_command, APP_DIR, BASE_DIR
ssh = connect_ssh()
cmd = (
    f"bash -lc \"source '{BASE_DIR}/activate' && cd '{APP_DIR}' && python - <<'PY'\n"
    "from app import create_app\n"
    "from models import User, Employee, Company, Meeting\n"
    "app = create_app()\n"
    "pages = [\n"
    "  '/meetings/',\n"
    "  '/agents/board',\n"
    "  '/agents/engineering',\n"
    "  '/agents/logs',\n"
    "  '/sapiens',\n"
    "]\n"
    "with app.app_context():\n"
    "    admin = User.query.filter(User.role.in_(['admin', 'administrator'])).order_by(User.id.asc()).first()\n"
    "    if not admin:\n"
    "        admin = User.query.order_by(User.id.asc()).first()\n"
    "    employee = Employee.query.filter_by(user_id=admin.id, status='active').order_by(Employee.id.asc()).first() if admin else None\n"
    "    first_company = Company.query.order_by(Company.id.asc()).first()\n"
    "    company_id = employee.company_id if employee else (first_company.id if first_company else 1)\n"
    "    meeting = Meeting.query.filter_by(company_id=company_id).order_by(Meeting.id.asc()).first()\n"
    "    if meeting:\n"
    "        pages.append('/meetings/company/{}/meeting/{}/report'.format(company_id, meeting.id))\n"
    "        pages.append('/meetings/company/{}'.format(company_id))\n"
    "    with app.test_client() as client:\n"
    "        if admin:\n"
    "            client.post('/login', json={'email': admin.email, 'password': '123456'})\n"
    "            client.post('/portal', json={'company_id': company_id})\n"
    "        for path in pages:\n"
    "            try:\n"
    "                resp = client.get(path, follow_redirects=False)\n"
    "                print('PAGE::{}::{}::{}'.format(path, resp.status_code, resp.headers.get('Location','')))\n"
    "                if resp.status_code >= 500:\n"
    "                    print(resp.get_data(as_text=True)[:1500])\n"
    "            except Exception as exc:\n"
    "                print('PAGE::{}::EXC::{}'.format(path, exc))\n"
    "PY\""
)
code, out, err = run_command(ssh, cmd)
print('CODE:', code)
if out: print('OUT:\n' + out)
if err: print('ERR:\n' + err)
ssh.close()
