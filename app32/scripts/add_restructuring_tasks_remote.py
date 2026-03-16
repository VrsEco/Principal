
import sys
import os
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parents[1]))
from scripts.deploy.configr_remote_helper import connect_ssh, APP_DIR

def run_remote():
    ssh = connect_ssh()
    try:
        local_script = Path(__file__).parent / "add_restructuring_tasks_logic.py"
        with open(local_script, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Base64 encode to avoid shell issues
        import base64
        b64_content = base64.b64encode(content.encode()).decode()
        
        remote_file = f"{APP_DIR}/add_restructuring_tasks_remote.py"
        
        # Upload
        print(f"Uploading script to {remote_file}...")
        ssh.exec_command(f"echo {b64_content} | base64 -d > {remote_file}")
        
        # Run
        python_bin = "/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/.virtualenv/3.12/bin/python"
        cmd = f"cd {APP_DIR} && {python_bin} {remote_file}"
        print(f"Running: {cmd}")
        stdin, stdout, stderr = ssh.exec_command(cmd)
        
        out = stdout.read().decode()
        err = stderr.read().decode()
        
        with open("scripts/add_tasks_output.txt", "w", encoding="utf-8") as f:
            f.write("--- STDOUT ---\n")
            f.write(out)
            f.write("\n--- STDERR ---\n")
            f.write(err)
        
        print("Done. Output written to scripts/add_tasks_output.txt")
        
        # Cleanup
        ssh.exec_command(f"rm {remote_file}")
        
    finally:
        ssh.close()

if __name__ == "__main__":
    run_remote()
