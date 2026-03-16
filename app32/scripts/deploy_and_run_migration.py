import sys
import os
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
from scripts.deploy.configr_remote_helper import connect_ssh, APP_DIR

def run():
    ssh = connect_ssh()
    try:
        # Transfere o script de migração via SFTP
        local_path = Path(__file__).parents[0] / "migrate_indicator_upgrade.py"
        remote_path = f"{APP_DIR}/scripts/migrate_indicator_upgrade.py"
        
        with open(local_path, "r", encoding="utf-8") as f:
            content = f.read()

        sftp = ssh.open_sftp()
        with sftp.open(remote_path, "w") as rf:
            rf.write(content)
        sftp.close()
        print(f"Arquivo transferido: {remote_path}")

        print("Executando migração em produção...")
        python_bin = "/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/.virtualenv/3.12/bin/python"
        cmd = f"cd {APP_DIR} && export FLASK_APP=app.py && {python_bin} scripts/migrate_indicator_upgrade.py 2>&1"
        _, stdout, _ = ssh.exec_command(cmd)

        out = stdout.read().decode('utf-8', 'ignore')
        # Filtra só linhas relevantes
        linhas = out.split('\n')
        relevantes = [
            l for l in linhas
            if not l.startswith('DEBUG') and not l.startswith('INFO')
            and not l.startswith('BOT') and not l.startswith('[SQUAD')
            and not l.startswith('WARNING')
        ]
        resultado = "\n".join(relevantes).encode('ascii', 'replace').decode('ascii')
        print(resultado)

    finally:
        ssh.close()

if __name__ == "__main__":
    run()
