import subprocess
import sys

cmd = [
    "ssh", 
    "-i", "deploy_key_SECRETA.txt", 
    "-p", "22122", 
    "-o", "StrictHostKeyChecking=no", 
    "app@ip-69-164-205-75.cloudezapp.io", 
    "/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/.virtualenv/3.12/bin/python3", 
    "/home/app/test_dashboard_prod.py"
]

try:
    print("Running command...")
    result = subprocess.run(cmd, env={"PGPASSWORD": "*Paraiso1978"}, capture_output=True, text=True, timeout=60)
    print("--- STDOUT ---")
    print(result.stdout)
    print("--- STDERR ---")
    print(result.stderr)
    print(f"--- EXIT CODE: {result.returncode} ---")
except Exception as e:
    print(f"Error: {e}")
