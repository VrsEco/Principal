
import subprocess
import os

key_path = "deploy_key_SECRETA.txt"
host = "app@69.164.205.75"
port = "22122"
remote_script = "/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/www/app32/scripts/deploy_configr.sh"

cmd = [
    "ssh",
    "-i", key_path,
    "-p", port,
    "-o", "StrictHostKeyChecking=no",
    "-o", "BatchMode=yes",
    host,
    f"bash {remote_script}"
]

print(f"FORCING DEPLOY AGAIN AND SAVING OUTPUT to file...")
try:
    with open("deploy_stdout.txt", "wb") as f_out, open("deploy_stderr.txt", "wb") as f_err:
        result = subprocess.run(cmd, stdout=f_out, stderr=f_err, timeout=180)
    print(f"Exit Code: {result.returncode}")
except Exception as e:
    print(f"Error: {e}")
