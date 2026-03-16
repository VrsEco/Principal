from scripts.deploy.configr_remote_helper import connect_ssh, run_command
ssh = connect_ssh()
cmd = "bash -lc \"source '/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/activate' && cd '/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/www/app32' && python -c \\\"import base64; exec(base64.b64decode('CmZyb20gYXBwIGltcG9ydCBjcmVhdGVfYXBwCmZyb20gcGF0aGxpYiBpbXBvcnQgUGF0aAppbXBvcnQgcmUKYXBwID0gY3JlYXRlX2FwcCgpCnZhbGlkID0ge3J1bGUuZW5kcG9pbnQgZm9yIHJ1bGUgaW4gYXBwLnVybF9tYXAuaXRlcl9ydWxlcygpfQpwYXR0ZXJuID0gcmUuY29tcGlsZShyInVybF9mb3JcKFsnXCJdKFteJ1wiXSspWydcIl0iKQpiYXNlID0gUGF0aCgndGVtcGxhdGVzJykKc2VlbiA9IFtdCmZvciBwYXRoIGluIGJhc2Uucmdsb2IoJyouaHRtbCcpOgogICAgdGV4dCA9IHBhdGgucmVhZF90ZXh0KGVuY29kaW5nPSd1dGYtOCcsIGVycm9ycz0naWdub3JlJykKICAgIGZvciBtIGluIHBhdHRlcm4uZmluZGl0ZXIodGV4dCk6CiAgICAgICAgZXAgPSBtLmdyb3VwKDEpCiAgICAgICAgaWYgZXAgbm90IGluIHZhbGlkOgogICAgICAgICAgICBzZWVuLmFwcGVuZCgoc3RyKHBhdGgpLCBlcCkpCmZvciBwYXRoLCBlcCBpbiBzb3J0ZWQoc2V0KHNlZW4pKToKICAgIHByaW50KCdNSVNTSU5HX0VORFBPSU5UOjp7fTo6e30nLmZvcm1hdChwYXRoLCBlcCkpCg==').decode('utf-8'))\\\"\""
code, out, err = run_command(ssh, cmd)
print('CODE:', code)
if out: print('OUT:\n'+out)
if err: print('ERR:\n'+err)
ssh.close()
