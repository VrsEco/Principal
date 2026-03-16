from scripts.deploy.configr_remote_helper import connect_ssh, run_command
ssh = connect_ssh()
cmd = '''bash -lc "source '/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/activate' && cd '/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/www/app32' && python - <<'PY'
from app import create_app
from flask import session
from api.routes.processes import process_details, process_book, process_instances_page
from api.routes.projects import project_manage, project_edit
from api.routes.meetings import meetings_company_manage, meeting_report
from api.routes.indicators import indicator_details, indicator_edit
import traceback
app = create_app()
tests = [
    ('PROCESS_DETAILS', '/processes/1', 9, lambda: process_details.__wrapped__(1) if hasattr(process_details,'__wrapped__') else process_details(1)),
    ('PROCESS_BOOK', '/processes/1/book', 9, lambda: process_book.__wrapped__(1) if hasattr(process_book,'__wrapped__') else process_book(1)),
    ('PROCESS_INSTANCES', '/companies/9/process-instances', 9, lambda: process_instances_page.__wrapped__(9) if hasattr(process_instances_page,'__wrapped__') else process_instances_page(9)),
    ('PROJECT_MANAGE', '/projects/4', 1, lambda: project_manage.__wrapped__(4) if hasattr(project_manage,'__wrapped__') else project_manage(4)),
    ('PROJECT_EDIT', '/projects/4/edit', 1, lambda: project_edit.__wrapped__(4) if hasattr(project_edit,'__wrapped__') else project_edit(4)),
    ('MEETINGS_COMPANY', '/meetings/company/1', 1, lambda: meetings_company_manage.__wrapped__(1) if hasattr(meetings_company_manage,'__wrapped__') else meetings_company_manage(1)),
    ('MEETING_REPORT', '/meetings/company/1/meeting/3/report', 1, lambda: meeting_report.__wrapped__(1,3) if hasattr(meeting_report,'__wrapped__') else meeting_report(1,3)),
    ('INDICATOR_DETAILS', '/indicators/1', 9, lambda: indicator_details.__wrapped__(1) if hasattr(indicator_details,'__wrapped__') else indicator_details(1)),
    ('INDICATOR_EDIT', '/indicators/1/edit', 9, lambda: indicator_edit.__wrapped__(1) if hasattr(indicator_edit,'__wrapped__') else indicator_edit(1)),
]
with app.app_context():
    for label, path, company_id, fn in tests:
        with app.test_request_context(path):
            session['active_company_id'] = company_id
            try:
                resp = fn()
                print('{}::OK::{}'.format(label, type(resp).__name__))
            except Exception as exc:
                print('{}::EXC::{}'.format(label, exc))
                print(traceback.format_exc())
PY"'''
code, out, err = run_command(ssh, cmd)
print('CODE:', code)
if out: print('OUT:\n'+out)
if err: print('ERR:\n'+err)
ssh.close()
