from scripts.deploy.configr_remote_helper import connect_ssh, run_command, APP_DIR, BASE_DIR
ssh = connect_ssh()
validate_cmd = (
    f"bash -lc \"source '{BASE_DIR}/activate' && cd '{APP_DIR}' && python - <<'PY'\n"
    "from app import create_app\n"
    "from flask import session\n"
    "from api.routes.incentives import dashboard\n"
    "from api.resources.incentive import IncentiveIndicatorListResource, IncentiveSpiderWebResource\n"
    "from models import IncentiveCalculation\n"
    "app = create_app()\n"
    "with app.app_context():\n"
    "    try:\n"
    "        last_calc = IncentiveCalculation.query.filter_by(company_id=1).order_by(IncentiveCalculation.created_at.desc()).first()\n"
    "        print('ORM_LAST_CALC::OK::{}'.format(getattr(last_calc, 'id', None)))\n"
    "    except Exception as exc:\n"
    "        print('ORM_LAST_CALC::EXC::{}'.format(exc))\n"
    "    with app.test_request_context('/incentives'):\n"
    "        session['active_company_id'] = 1\n"
    "        try:\n"
    "            resp = dashboard.__wrapped__() if hasattr(dashboard, '__wrapped__') else dashboard()\n"
    "            print('DASHBOARD::OK::{}'.format(type(resp).__name__))\n"
    "        except Exception as exc:\n"
    "            print('DASHBOARD::EXC::{}'.format(exc))\n"
    "    with app.test_request_context('/api/incentives/indicators'):\n"
    "        session['active_company_id'] = 1\n"
    "        try:\n"
    "            data = IncentiveIndicatorListResource().get()\n"
    "            print('API_INDICATORS::OK::{}'.format(len(data) if isinstance(data, list) else type(data).__name__))\n"
    "        except Exception as exc:\n"
    "            print('API_INDICATORS::EXC::{}'.format(exc))\n"
    "    with app.test_request_context('/api/incentives/spider-web-data'):\n"
    "        session['active_company_id'] = 1\n"
    "        try:\n"
    "            data = IncentiveSpiderWebResource().get()\n"
    "            print('SPIDER::OK::{}'.format(len(data.get('nodes', [])) if isinstance(data, dict) else type(data).__name__))\n"
    "        except Exception as exc:\n"
    "            print('SPIDER::EXC::{}'.format(exc))\n"
    "PY\""
)
ssh = connect_ssh()
try:
    code, out, err = run_command(ssh, validate_cmd)
    print('CODE:', code)
    if out:
        print('OUT:\n' + out)
    if err:
        print('ERR:\n' + err)
finally:
    ssh.close()
