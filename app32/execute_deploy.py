
import subprocess
import os

key_path = r"c:\GestaoVersus\github_actions_deploy_key.txt"
host = "app@69.164.205.75"
port = "22122"
remote_script = "/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/www/app32/scripts/deploy_configr.sh"

cmd = [
    "ssh",
    "-i", key_path,
    "-p", port,
    "-o", "StrictHostKeyChecking=no",
    host,
    f"bash {remote_script}"
]

print(f"Executing: {' '.join(cmd)}")
try:
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    print("--- STDOUT ---")
    print(result.stdout)
    print("--- STDERR ---")
    print(result.stderr)
    print(f"Exit Code: {result.returncode}")
except Exception as e:
    print(f"Error: {e}")
