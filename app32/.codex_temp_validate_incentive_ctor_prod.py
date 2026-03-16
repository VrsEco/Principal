from scripts.deploy.configr_remote_helper import connect_ssh, run_command, APP_DIR, BASE_DIR
ssh = connect_ssh()
cmd = (
    f"bash -lc \"source '{BASE_DIR}/activate' && cd '{APP_DIR}' && python - <<'PY'\n"
    "from app import create_app\n"
    "from models import IncentiveRule, IncentiveCalculation\n"
    "app = create_app()\n"
    "with app.app_context():\n"
    "    try:\n"
    "        rule = IncentiveRule(company_id=1, rule_set_id=1, indicator_id=1, impact_value=1.5, max_reduction=0.3)\n"
    "        print('CTOR_RULE::OK::{}::{}'.format(rule.weight, rule.max_reduction))\n"
    "    except Exception as exc:\n"
    "        print('CTOR_RULE::EXC::{}'.format(exc))\n"
    "    try:\n"
    "        calc = IncentiveCalculation(company_id=1, rule_set_id=1, period_start=None, period_end=None, results_payload={'participants': []})\n"
    "        print('CTOR_CALC::OK::{}'.format(calc.results_payload))\n"
    "    except Exception as exc:\n"
    "        print('CTOR_CALC::EXC::{}'.format(exc))\n"
    "PY\""
)
code, out, err = run_command(ssh, cmd)
print('CODE:', code)
if out:
    print('OUT:\n' + out)
if err:
    print('ERR:\n' + err)
ssh.close()
