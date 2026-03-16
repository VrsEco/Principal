import sys
import os
from pathlib import Path
import base64

sys.path.append(str(Path(__file__).resolve().parents[1]))
from scripts.deploy.configr_remote_helper import connect_ssh, APP_DIR

def run():
    ssh = connect_ssh()
    try:
        local_path = Path(__file__).parents[0] / "remote_update_aa_j_31.py"
        with open(local_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Transfer via sftp para evitar problemas de escape/base64
        sftp = ssh.open_sftp()
        remote_path = f"{APP_DIR}/scripts/remote_update_aa_j_31.py"
        with sftp.open(remote_path, "w") as rf:
            rf.write(content)
        sftp.close()
        print(f"Arquivo transferido para {remote_path}")
        
        print("Executando script em producao...")
        python_bin = "/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/.virtualenv/3.12/bin/python"
        cmd = f"cd {APP_DIR} && export FLASK_APP=app.py && {python_bin} scripts/remote_update_aa_j_31.py 2>&1"
        stdin, stdout, stderr = ssh.exec_command(cmd)
        
        out = stdout.read().decode('utf-8', 'ignore')
        # Mostra apenas as linhas relevantes (filtra logs de inicializacao)
        linhas = out.split('\n')
        relevantes = [l for l in linhas if not l.startswith('DEBUG') and not l.startswith('INFO') and not l.startswith('BOT') and not l.startswith('[SQUAD')]
        print("\n".join(relevantes).encode('ascii', 'replace').decode('ascii'))
            
    finally:
        ssh.close()

if __name__ == "__main__":
    run()
