
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
    "cat /srv/appgestaoversuscombr.45a4cd4b.configr.cloud/www/app32/.env"
]

try:
    with open("remote_env.txt", "wb") as f:
        result = subprocess.run(cmd, stdout=f, timeout=30)
    # Masking keys for print
    with open("remote_env.txt", "r", encoding='latin-1', errors='replace') as f:
        content = f.read()
        masked = ""
        for line in content.splitlines():
            if '=' in line:
                k, v = line.split('=', 1)
                masked += f"{k}=***{v[-4:] if len(v)>4 else ''}\n"
            else:
                masked += line + "\n"
        print(masked)
except Exception as e:
    print(f"Error: {e}")
