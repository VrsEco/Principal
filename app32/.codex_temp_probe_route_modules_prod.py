from scripts.deploy.configr_remote_helper import connect_ssh, run_command, APP_DIR, BASE_DIR
ssh = connect_ssh()
cmd = (
    f"bash -lc \"source '{BASE_DIR}/activate' && cd '{APP_DIR}' && python - <<'PY'\n"
    "mods = ['api.routes.indicators','api.routes.processes','api.routes.projects','api.routes.meetings','api.routes.agents']\n"
    "for mod_name in mods:\n"
    "    m = __import__(mod_name, fromlist=['*'])\n"
    "    names = [n for n in dir(m) if not n.startswith('_')]\n"
    "    print('MODULE::' + mod_name)\n"
    "    print(names[:200])\n"
    "PY\""
)
code, out, err = run_command(ssh, cmd)
print('CODE:', code)
if out: print('OUT:\n'+out)
if err: print('ERR:\n'+err)
ssh.close()
