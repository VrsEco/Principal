from scripts.deploy.configr_remote_helper import connect_ssh, run_command, APP_DIR, BASE_DIR
ssh = connect_ssh()
cmd = (
    f"bash -lc \"source '{BASE_DIR}/activate' && cd '{APP_DIR}' && python - <<'PY'\n"
    "from app import create_app\n"
    "from flask import session\n"
    "from api.routes.processes import process_instances_page, process_occurrences_page, process_routines_page, process_routines_analysis_page\n"
    "import traceback\n"
    "app = create_app()\n"
    "tests = [\n"
    " ('PROCESS_INSTANCES', '/companies/1/process-instances', lambda: process_instances_page.__wrapped__(1) if hasattr(process_instances_page,'__wrapped__') else process_instances_page(1)),\n"
    " ('PROCESS_OCCURRENCES', '/companies/1/process-occurrences', lambda: process_occurrences_page.__wrapped__(1) if hasattr(process_occurrences_page,'__wrapped__') else process_occurrences_page(1)),\n"
    " ('PROCESS_ROUTINES', '/companies/1/process-routines', lambda: process_routines_page.__wrapped__(1) if hasattr(process_routines_page,'__wrapped__') else process_routines_page(1)),\n"
    " ('PROCESS_ROUTINES_ANALYSIS', '/companies/1/process-routines/analysis', lambda: process_routines_analysis_page.__wrapped__(1) if hasattr(process_routines_analysis_page,'__wrapped__') else process_routines_analysis_page(1)),\n"
    "]\n"
    "with app.app_context():\n"
    "    for label, path, fn in tests:\n"
    "        with app.test_request_context(path):\n"
    "            session['active_company_id'] = 1\n"
    "            try:\n"
    "                resp = fn()\n"
    "                print('{}::OK::{}'.format(label, type(resp).__name__))\n"
    "            except Exception as exc:\n"
    "                print('{}::EXC::{}'.format(label, exc))\n"
    "                print(traceback.format_exc())\n"
    "PY\""
)
code, out, err = run_command(ssh, cmd)
print('CODE:', code)
if out: print('OUT:\n'+out)
if err: print('ERR:\n'+err)
ssh.close()
