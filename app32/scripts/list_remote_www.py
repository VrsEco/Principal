
import subprocess
import json

cmd = [
    "ssh", 
    "-i", "deploy_key_SECRETA.txt", 
    "-p", "22122", 
    "-o", "StrictHostKeyChecking=no", 
    "app@ip-69-164-205-75.cloudezapp.io", 
    "ls -1 /srv/appgestaoversuscombr.45a4cd4b.configr.cloud/www/"
]

try:
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    print(result.stdout)
except Exception as e:
    print(f"Error: {e}")
