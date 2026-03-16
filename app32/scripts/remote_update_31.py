
import sys
import os
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
from scripts.deploy.configr_remote_helper import connect_ssh, APP_DIR

def run_remote():
    ssh = connect_ssh()
    try:
        local_script = Path(__file__).parent / "update_aa_j_31_prod_logic.py"
        with open(local_script, "r", encoding="utf-8") as f:
            content = f.read()
        
        import base64
        b64_content = base64.b64encode(content.encode()).decode()
        remote_file = f"{APP_DIR}/update_aa_j_31_prod_remote.py"
        
        print(f"Uploading script to {remote_file}...")
        ssh.exec_command(f"echo {b64_content} | base64 -d > {remote_file}")
        
        python_bin = "/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/.virtualenv/3.12/bin/python"
        cmd = f"cd {APP_DIR} && {python_bin} {remote_file}"
        print(f"Running: {cmd}")
        stdin, stdout, stderr = ssh.exec_command(cmd)
        
        out = stdout.read().decode()
        err = stderr.read().decode()
        
        with open("scripts/update_output.txt", "w", encoding="utf-8") as f:
            f.write("--- STDOUT ---\n")
            f.write(out)
            f.write("\n--- STDERR ---\n")
            f.write(err)
        
        print("Done. Output written to scripts/update_output.txt")
        ssh.exec_command(f"rm {remote_file}")
        
    finally:
        ssh.close()

if __name__ == "__main__":
    run_remote()
