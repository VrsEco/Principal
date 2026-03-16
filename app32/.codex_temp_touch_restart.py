from scripts.deploy.configr_remote_helper import connect_ssh, run_command, APP_DIR
ssh = connect_ssh()
code, out, err = run_command(ssh, f"touch '{APP_DIR}/restart.txt'")
print(code)
print(out)
print(err)
ssh.close()
