from scripts.deploy.configr_remote_helper import connect_ssh, run_command, APP_DIR, BASE_DIR
ssh = connect_ssh()
cmd = (
    f"bash -lc \"source '{BASE_DIR}/activate' && cd '{APP_DIR}' && python - <<'PY'\n"
    "from app import create_app\n"
    "from flask import session\n"
    "from api.routes.incentives import manage_rules, participant_add, vetor_add, vetor_update, closing_report\n"
    "from models import IncentiveRuleSet, IncentiveRule, IncentiveCalculation\n"
    "import traceback\n"
    "app = create_app()\n"
    "def call(label, path, fn, method='GET', json=None):\n"
    "    with app.test_request_context(path, method=method, json=json):\n"
    "        session['active_company_id'] = 1\n"
    "        try:\n"
    "            resp = fn()\n"
    "            print('{}::OK::{}'.format(label, type(resp).__name__))\n"
    "        except Exception as exc:\n"
    "            print('{}::EXC::{}'.format(label, exc))\n"
    "            print(traceback.format_exc())\n"
    "with app.app_context():\n"
    "    rs = IncentiveRuleSet.query.filter_by(company_id=1).order_by(IncentiveRuleSet.id.asc()).first()\n"
    "    print('RULESET::{}'.format(getattr(rs, 'id', None)))\n"
    "    if rs:\n"
    "        call('MANAGE', f'/incentives/rules/{rs.id}', lambda: manage_rules.__wrapped__(rs.id) if hasattr(manage_rules, '__wrapped__') else manage_rules(rs.id))\n"
    "        call('PARTICIPANT_ADD', f'/incentives/rules/{rs.id}/participants', lambda: participant_add.__wrapped__(rs.id) if hasattr(participant_add, '__wrapped__') else participant_add(rs.id), method='POST', json={'employee_id': 1, 'valor_base': 1000})\n"
    "        call('VETOR_ADD', f'/incentives/rules/{rs.id}/vetores', lambda: vetor_add.__wrapped__(rs.id) if hasattr(vetor_add, '__wrapped__') else vetor_add(rs.id), method='POST', json={'indicator_id': 1, 'impact_value': 1.2})\n"
    "    v = IncentiveRule.query.filter_by(company_id=1).order_by(IncentiveRule.id.asc()).first()\n"
    "    print('VETOR::{}'.format(getattr(v, 'id', None)))\n"
    "    if v:\n"
    "        call('VETOR_UPDATE', f'/incentives/vetores/{v.id}', lambda: vetor_update.__wrapped__(v.id) if hasattr(vetor_update, '__wrapped__') else vetor_update(v.id), method='PATCH', json={'impact_value': 1.1})\n"
    "    calc = IncentiveCalculation.query.filter_by(company_id=1).order_by(IncentiveCalculation.id.asc()).first()\n"
    "    print('CALC::{}'.format(getattr(calc, 'id', None)))\n"
    "    if calc:\n"
    "        call('CLOSING', f'/incentives/closing/{calc.id}', lambda: closing_report.__wrapped__(calc.id) if hasattr(closing_report, '__wrapped__') else closing_report(calc.id))\n"
    "PY\""
)
code, out, err = run_command(ssh, cmd)
print('CODE:', code)
if out: print('OUT:\n'+out)
if err: print('ERR:\n'+err)
ssh.close()
