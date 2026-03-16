from scripts.deploy.configr_remote_helper import connect_ssh, run_command, APP_DIR, BASE_DIR
ssh = connect_ssh()
cmd = (
    f"bash -lc \"source '{BASE_DIR}/activate' && cd '{APP_DIR}' && python - <<'PY'\n"
    "from app import create_app\n"
    "from models import IncentiveRuleSet, IncentiveParticipant, IncentiveRule, Employee\n"
    "from services.incentive_service import IncentiveService\n"
    "from datetime import date\n"
    "import traceback\n"
    "app = create_app()\n"
    "with app.app_context():\n"
    "    company_id = 1\n"
    "    rs = IncentiveRuleSet.query.filter_by(company_id=company_id, is_active=True).first()\n"
    "    print('ACTIVE_RULESET::{}'.format(getattr(rs, 'id', None)))\n"
    "    if rs:\n"
    "        print('RULES::{}'.format(IncentiveRule.query.filter_by(rule_set_id=rs.id).count()))\n"
    "        print('PARTICIPANTS::{}'.format(IncentiveParticipant.query.filter_by(rule_set_id=rs.id, company_id=company_id).count()))\n"
    "    print('EMPLOYEES::{}'.format(Employee.query.filter_by(company_id=company_id).count()))\n"
    "    if rs:\n"
    "        try:\n"
    "            today = date.today()\n"
    "            res = IncentiveService.calculate_incentive(company_id, rs.id, date(today.year, today.month, 1), today)\n"
    "            print('CALC_RESULT::{}'.format(res))\n"
    "        except Exception as exc:\n"
    "            print('CALC_EXC::{}'.format(exc))\n"
    "            print(traceback.format_exc())\n"
    "PY\""
)
code, out, err = run_command(ssh, cmd)
print('CODE:', code)
if out: print('OUT:\n' + out)
if err: print('ERR:\n' + err)
ssh.close()
