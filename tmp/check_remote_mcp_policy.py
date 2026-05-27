import sys
from pathlib import Path
repo = Path(r'C:\GestaoVersus\app32\app32')
sys.path.insert(0, str(repo))
from scripts.deploy.configr_remote_helper import connect_ssh, run_command, APP_DIR
ssh = connect_ssh()
cmd = f"cd {APP_DIR}/app32 && . ../.env >/dev/null 2>&1; PYTHONPATH=. python -c \"from src.intelligence.security.mcp_mutation_guard import load_mutation_limit_policy; p=load_mutation_limit_policy(); print({{'create_limit': p.create_limit, 'update_limit': p.update_limit, 'window_hours': p.window_hours}})\""
code, out, err = run_command(ssh, cmd)
print(out)
print(err)
print(f"[EXIT_CODE]={code}")
ssh.close()
