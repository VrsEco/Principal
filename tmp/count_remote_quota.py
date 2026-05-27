import sys
from pathlib import Path
repo = Path(r'C:\GestaoVersus\app32\app32')
sys.path.insert(0, str(repo))
from scripts.deploy.configr_remote_helper import connect_ssh, run_command, APP_DIR
ssh = connect_ssh()
remote_cmd = (
    f"cd {APP_DIR} && "
    f"PYTHONPATH=. /srv/appgestaoversuscombr.45a4cd4b.configr.cloud/.virtualenv/3.12/bin/python -c \""
    "import os; "
    "from dotenv import load_dotenv; load_dotenv('.env'); "
    "os.environ.setdefault('FLASK_CONFIG','production'); "
    "os.environ['APP_BOOTSTRAP_DB_SCHEMA']='0'; os.environ['APP_BOOTSTRAP_RUNTIME_SERVICES']='0'; "
    "from app import create_app; "
    "from src.intelligence.security.mcp_mutation_guard import load_mutation_limit_policy, count_recent_mutations; "
    "app=create_app('production'); "
    "ctx=app.app_context(); ctx.push(); "
    "p=load_mutation_limit_policy(); "
    "print({'create_limit': p.create_limit, 'window_hours': p.window_hours, 'count_company11_user3': count_recent_mutations(action='create', company_id=11, user_id=3)}); "
    "ctx.pop()"
    "\""
)
code, out, err = run_command(ssh, remote_cmd)
print(out)
print(err)
print(f"[EXIT_CODE]={code}")
ssh.close()
