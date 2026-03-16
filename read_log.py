#!/usr/bin/env python3
import subprocess

result = subprocess.run(
    ['tail', '-n', '80', '/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/log/uwsgi/uwsgi.log'],
    capture_output=True, text=True
)
print(result.stdout)
print(result.stderr)
