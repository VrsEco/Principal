from scripts.deploy.configr_remote_helper import connect_ssh, run_command, APP_DIR
ssh = connect_ssh()
cmd = f"bash -lc \"cd '{APP_DIR}' && grep -n \"const instanceId = currentActivity.instance_id || currentActivity.id;\" static/js/my-work.js\""
code, out, err = run_command(ssh, cmd)
print('CODE:', code)
if out: print('OUT:\n' + out)
if err: print('ERR:\n' + err)
ssh.close()
