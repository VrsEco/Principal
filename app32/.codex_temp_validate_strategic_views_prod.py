from scripts.deploy.configr_remote_helper import connect_ssh, run_command, APP_DIR, BASE_DIR
ssh = connect_ssh()
cmd = (
    f"bash -lc \"source '{BASE_DIR}/activate' && cd '{APP_DIR}' && python - <<'PY'\n"
    "from app import create_app\n"
    "from flask import session\n"
    "from api.routes.indicators import indicators_list, indicator_analysis\n"
    "from api.routes.processes import processes_list, process_map, process_instances_page\n"
    "from api.routes.projects import projects_list, project_analysis\n"
    "from api.routes.meetings import meetings_manage_root\n"
    "from api.routes.agents import ai_board, get_engineering_board, workflow_approval_board\n"
    "import traceback\n"
    "app = create_app()\n"
    "tests = [\n"
    " ('INDICATORS', '/indicators', lambda: indicators_list.__wrapped__() if hasattr(indicators_list,'__wrapped__') else indicators_list()),\n"
    " ('INDICATOR_ANALYSIS', '/indicators/analysis', lambda: indicator_analysis.__wrapped__() if hasattr(indicator_analysis,'__wrapped__') else indicator_analysis()),\n"
    " ('PROCESSES', '/processes', lambda: processes_list.__wrapped__() if hasattr(processes_list,'__wrapped__') else processes_list()),\n"
    " ('PROCESS_MAP', '/process-map', lambda: process_map.__wrapped__() if hasattr(process_map,'__wrapped__') else process_map()),\n"
    " ('PROCESS_INSTANCES', '/processes/instances', lambda: process_instances_page.__wrapped__() if hasattr(process_instances_page,'__wrapped__') else process_instances_page()),\n"
    " ('PROJECTS', '/projects', lambda: projects_list.__wrapped__() if hasattr(projects_list,'__wrapped__') else projects_list()),\n"
    " ('PROJECT_ANALYSIS', '/projects/analysis', lambda: project_analysis.__wrapped__() if hasattr(project_analysis,'__wrapped__') else project_analysis()),\n"
    " ('MEETINGS', '/meetings/', lambda: meetings_manage_root.__wrapped__() if hasattr(meetings_manage_root,'__wrapped__') else meetings_manage_root()),\n"
    " ('AGENTS_BOARD', '/agents/board', lambda: ai_board.__wrapped__() if hasattr(ai_board,'__wrapped__') else ai_board()),\n"
    " ('AGENTS_ENGINEERING', '/agents/engineering', lambda: get_engineering_board.__wrapped__() if hasattr(get_engineering_board,'__wrapped__') else get_engineering_board()),\n"
    " ('AGENTS_APPROVALS', '/api/agents/actions/workflow-approvals/board', lambda: workflow_approval_board.__wrapped__() if hasattr(workflow_approval_board,'__wrapped__') else workflow_approval_board()),\n"
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
