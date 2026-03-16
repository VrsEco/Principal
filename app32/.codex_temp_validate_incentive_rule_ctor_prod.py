from scripts.deploy.configr_remote_helper import connect_ssh, run_command, APP_DIR, BASE_DIR
ssh = connect_ssh()
cmd = (
    f"bash -lc \"source '{BASE_DIR}/activate' && cd '{APP_DIR}' && python - <<'PY'\n"
    "from app import create_app\n"
    "from models import IncentiveRule\n"
    "app = create_app()\n"
    "with app.app_context():\n"
    "    try:\n"
    "        rule = IncentiveRule(company_id=1, rule_set_id=1, indicator_id=1, impact_value=1.5, max_reduction=0.3, ranges_config=[{'color':'green','value':1.2}], calculation_mode='ranges', use_indicator_goal=True)\n"
    "        print('CTOR_RULE::OK::{}::{}::{}::{}'.format(rule.weight, rule.ranges_config, rule.calculation_mode, rule.use_indicator_goal))\n"
    "        print('TO_DICT::{}'.format(rule.to_dict()))\n"
    "    except Exception as exc:\n"
    "        print('CTOR_RULE::EXC::{}'.format(exc))\n"
    "PY\""
)
code, out, err = run_command(ssh, cmd)
print('CODE:', code)
if out: print('OUT:\n'+out)
if err: print('ERR:\n'+err)
ssh.close()
