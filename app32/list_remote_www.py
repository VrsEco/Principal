
import subprocess
import os

key_path = "deploy_key_SECRETA.txt"
host = "app@69.164.205.75"
port = "22122"

cmd = [
    "ssh",
    "-i", key_path,
    "-p", port,
    "-o", "StrictHostKeyChecking=no",
    "-o", "BatchMode=yes",
    host,
    "ls -F /srv/appgestaoversuscombr.45a4cd4b.configr.cloud/www/"
]

try:
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    print(result.stdout)
except Exception as e:
    print(f"Error: {e}")
