
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
    "cat /srv/appgestaoversuscombr.45a4cd4b.configr.cloud/www/passenger_wsgi.py"
]

try:
    with open("remote_passenger.txt", "wb") as f:
        result = subprocess.run(cmd, stdout=f, timeout=30)
    print(f"File saved. Exit code: {result.returncode}")
except Exception as e:
    print(f"Error: {e}")
