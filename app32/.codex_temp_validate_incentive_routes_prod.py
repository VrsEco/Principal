from scripts.deploy.configr_remote_helper import connect_ssh, run_command, APP_DIR, BASE_DIR
ssh = connect_ssh()
cmd = (
    f"bash -lc \"source '{BASE_DIR}/activate' && cd '{APP_DIR}' && python - <<'PY'\n"
    "from app import create_app\n"
    "from flask import session\n"
    "from models import Employee\n"
    "from api.routes.incentives import reports_selector, validation_panel, calculate_run, trigger_harvest, statement\n"
    "import traceback\n"
    "app = create_app()\n"
    "def run(label, path, fn):\n"
    "    with app.test_request_context(path, method='POST' if 'harvest' in path else 'GET'):\n"
    "        session['active_company_id'] = 1\n"
    "        try:\n"
    "            resp = fn()\n"
    "            print('{}::OK::{}'.format(label, type(resp).__name__))\n"
    "        except Exception as exc:\n"
    "            print('{}::EXC::{}'.format(label, exc))\n"
    "            print(traceback.format_exc())\n"
    "with app.app_context():\n"
    "    emp = Employee.query.filter_by(company_id=1).order_by(Employee.id.asc()).first()\n"
    "    run('REPORTS', '/incentives/reports', lambda: reports_selector.__wrapped__() if hasattr(reports_selector, '__wrapped__') else reports_selector())\n"
    "    run('VALIDATION', '/incentives/validation', lambda: validation_panel.__wrapped__() if hasattr(validation_panel, '__wrapped__') else validation_panel())\n"
    "    run('CALCULATE', '/incentives/calculate/run', lambda: calculate_run.__wrapped__() if hasattr(calculate_run, '__wrapped__') else calculate_run())\n"
    "    run('HARVEST', '/incentives/harvest/run', lambda: trigger_harvest.__wrapped__() if hasattr(trigger_harvest, '__wrapped__') else trigger_harvest())\n"
    "    if emp:\n"
    "        run('STATEMENT', '/incentives/statement', lambda: statement.__wrapped__(None, emp.id) if hasattr(statement, '__wrapped__') else statement(None, emp.id))\n"
    "PY\""
)
code, out, err = run_command(ssh, cmd)
print('CODE:', code)
if out: print('OUT:\n' + out)
if err: print('ERR:\n' + err)
ssh.close()
