
import subprocess
import os

key_path = r"c:\GestaoVersus\github_actions_deploy_key.txt"
host = "app@69.164.205.75"
port = "22122"
remote_cmd = "cd /srv/appgestaoversuscombr.45a4cd4b.configr.cloud/www/app32 && git log -n 1 --oneline"

cmd = [
    "ssh",
    "-i", key_path,
    "-p", port,
    "-o", "StrictHostKeyChecking=no",
    "-o", "BatchMode=yes",
    host,
    f"bash -c '{remote_cmd}'"
]

print(f"Executing: {' '.join(cmd)}")
try:
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    print("--- STDOUT ---")
    print(result.stdout)
    print("--- STDERR ---")
    print(result.stderr)
    print(f"Exit Code: {result.returncode}")
except Exception as e:
    print(f"Error: {e}")
