from scripts.deploy.configr_remote_helper import connect_ssh, run_command, APP_DIR, BASE_DIR

ssh = connect_ssh()
cmd = (
    f"bash -lc \"source '{BASE_DIR}/activate' && cd '{APP_DIR}' && python - <<'PY'\n"
    "from app import create_app\n"
    "from models import User, Employee, Company\n"
    "app = create_app()\n"
    "paths = [\n"
    "  '/portal',\n"
    "  '/my-work',\n"
    "  '/incentives',\n"
    "  '/incentives/reports',\n"
    "  '/incentives/validation',\n"
    "  '/incentives/statement',\n"
    "  '/indicators',\n"
    "  '/indicators/analysis',\n"
    "  '/projects',\n"
    "  '/projects/analysis',\n"
    "  '/meetings/',\n"
    "  '/agents/board',\n"
    "  '/usuarios',\n"
    "]\n"
    "with app.app_context():\n"
    "    admin = User.query.filter(User.role.in_(['admin', 'administrator'])).order_by(User.id.asc()).first()\n"
    "    if not admin:\n"
    "        admin = User.query.order_by(User.id.asc()).first()\n"
    "    employee = Employee.query.filter_by(user_id=admin.id, status='active').order_by(Employee.id.asc()).first() if admin else None\n"
    "    first_company = Company.query.order_by(Company.id.asc()).first()\n"
    "    company_id = employee.company_id if employee else (first_company.id if first_company else 1)\n"
    "    print('LOGIN_USER::{}::COMPANY::{}'.format(getattr(admin, 'email', None), company_id))\n"
    "    with app.test_client() as client:\n"
    "        if admin:\n"
    "            resp = client.post('/login', json={'email': admin.email, 'password': '123456'})\n"
    "            print('LOGIN_STATUS::{}::{}'.format(resp.status_code, resp.get_json()))\n"
    "            portal_resp = client.post('/portal', json={'company_id': company_id})\n"
    "            print('PORTAL_SET::{}::{}'.format(portal_resp.status_code, portal_resp.get_json()))\n"
    "        for path in paths:\n"
    "            try:\n"
    "                resp = client.get(path, follow_redirects=False)\n"
    "                print('PAGE::{}::{}'.format(path, resp.status_code))\n"
    "                if resp.status_code >= 500:\n"
    "                    print(resp.get_data(as_text=True)[:1500])\n"
    "            except Exception as exc:\n"
    "                print('PAGE::{}::EXC::{}'.format(path, exc))\n"
    "PY\""
)
code, out, err = run_command(ssh, cmd)
print('CODE:', code)
if out:
    print('OUT:\n' + out)
if err:
    print('ERR:\n' + err)
ssh.close()
