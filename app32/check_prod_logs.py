
import subprocess
import os

key_path = "deploy_key_SECRETA.txt"
host = "app@69.164.205.75"
port = "22122"
log_path = "/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/logs/startup_error.log"

cmd = [
    "ssh",
    "-i", key_path,
    "-p", port,
    "-o", "StrictHostKeyChecking=no",
    "-o", "BatchMode=yes",
    host,
    f"tail -n 20 {log_path}"
]

print(f"Checking logs on server...")
try:
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    print("--- STDOUT ---")
    print(result.stdout)
    print("--- STDERR ---")
    print(result.stderr)
except Exception as e:
    print(f"Error: {e}")
