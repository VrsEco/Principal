from scripts.deploy.configr_remote_helper import connect_ssh, run_command, APP_DIR, BASE_DIR
ssh = connect_ssh()
try:
    cmds = [
        'pwd',
        f"ls -la '{BASE_DIR}'",
        f"ls -la '{APP_DIR}' | sed -n '1,60p'",
        'which python3 || which python || true',
        f"find '{BASE_DIR}' -maxdepth 3 -type f \\( -name python -o -name python3 \\) 2>/dev/null | head"
    ]
    for cmd in cmds:
        code, out, err = run_command(ssh, cmd)
        print('CMD:', cmd)
        print('CODE:', code)
        print('OUT:\n' + out if out else 'OUT:')
        print('ERR:\n' + err if err else 'ERR:')
finally:
    ssh.close()
