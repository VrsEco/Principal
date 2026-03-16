
import sys
import os
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parents[1]))
from scripts.deploy.configr_remote_helper import connect_ssh, APP_DIR

def run_remote():
    ssh = connect_ssh()
    try:
        local_script = Path(__file__).parent / "test_app_init.py"
        with open(local_script, "r", encoding="utf-8") as f:
            content = f.read()
            
        import base64
        b64_content = base64.b64encode(content.encode()).decode()
        remote_file = f"{APP_DIR}/test_app_init_remote_worker.py"
        
        print(f"Uploading script to {remote_file}...")
        ssh.exec_command(f"echo {b64_content} | base64 -d > {remote_file}")
        
        python_bin = "/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/.virtualenv/3.12/bin/python"
        cmd = f"cd {APP_DIR} && {python_bin} {remote_file}"
        print(f"Running: {cmd}")
        stdin, stdout, stderr = ssh.exec_command(cmd)
        
        out = stdout.read().decode()
        err = stderr.read().decode()
        
        print("STDOUT:")
        print(out)
        print("STDERR:")
        print(err)
        
        ssh.exec_command(f"rm {remote_file}")
    finally:
        ssh.close()

if __name__ == "__main__":
    run_remote()
