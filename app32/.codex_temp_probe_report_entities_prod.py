from scripts.deploy.configr_remote_helper import connect_ssh, run_command, APP_DIR, BASE_DIR
ssh = connect_ssh()
cmd = (
    f"bash -lc \"source '{BASE_DIR}/activate' && cd '{APP_DIR}' && python - <<'PY'\n"
    "from app import create_app\n"
    "from models import User, Employee, Company, Project, ProjectTask, Process, Meeting\n"
    "app = create_app()\n"
    "with app.app_context():\n"
    "    admin = User.query.filter(User.role.in_(['admin','administrator'])).order_by(User.id.asc()).first()\n"
    "    if not admin:\n"
    "        admin = User.query.order_by(User.id.asc()).first()\n"
    "    print('ADMIN::{}'.format(getattr(admin, 'email', None)))\n"
    "    p = Process.query.order_by(Process.company_id.asc(), Process.id.asc()).first()\n"
    "    prj = Project.query.order_by(Project.company_id.asc(), Project.id.asc()).first()\n"
    "    task = ProjectTask.query.join(Project, Project.id == ProjectTask.project_id).order_by(Project.company_id.asc(), ProjectTask.id.asc()).first()\n"
    "    meeting = Meeting.query.order_by(Meeting.company_id.asc(), Meeting.id.asc()).first()\n"
    "    print('PROCESS::{}::company={}'.format(getattr(p, 'id', None), getattr(p, 'company_id', None)))\n"
    "    print('PROJECT::{}::company={}'.format(getattr(prj, 'id', None), getattr(prj, 'company_id', None)))\n"
    "    print('TASK::{}::project={}'.format(getattr(task, 'id', None), getattr(task, 'project_id', None)))\n"
    "    print('MEETING::{}::company={}'.format(getattr(meeting, 'id', None), getattr(meeting, 'company_id', None)))\n"
    "PY\""
)
code, out, err = run_command(ssh, cmd)
print('CODE:', code)
if out: print('OUT:\n' + out)
if err: print('ERR:\n' + err)
ssh.close()
