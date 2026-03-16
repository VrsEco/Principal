import sys
import os
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
from scripts.deploy.configr_remote_helper import connect_ssh, APP_DIR

def run():
    ssh = connect_ssh()
    try:
        python_bin = "/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/.virtualenv/3.12/bin/python"
        # Verifica colunas da tabela indicators remotamente
        check_code = """
import sys, os
sys.path.append('/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/www/app32')
from app import create_app
from models import db
from sqlalchemy import text
app = create_app()
with app.app_context():
    cols_needed = ['tree_id','full_code','group_id','polarity','formula',
                   'process_id','project_id','collaborators','data_source',
                   'okr_reference','okr_level']
    conn = db.engine.connect()
    for col in cols_needed:
        r = conn.execute(text(
            "SELECT COUNT(*) FROM information_schema.columns WHERE table_name='indicators' AND column_name=:c"
        ), {'c': col})
        exists = r.scalar() > 0
        print(f"  {'OK' if exists else 'FALTA'} - {col}")
    conn.close()
    print('VERIFICACAO CONCLUIDA')
"""
        cmd = f"cd {APP_DIR} && export FLASK_APP=app.py && {python_bin} -c \"{check_code.strip().replace(chr(10), '; ')}\""
        
        # Usa arquivo temporário para evitar escaping
        sftp = ssh.open_sftp()
        with sftp.open(f"{APP_DIR}/scripts/_tmp_check.py", "w") as f:
            f.write(check_code)
        sftp.close()
        
        _, stdout, _ = ssh.exec_command(
            f"cd {APP_DIR} && export FLASK_APP=app.py && {python_bin} scripts/_tmp_check.py 2>&1"
        )
        out = stdout.read().decode('utf-8', 'ignore')
        linhas = [l for l in out.split('\n') if not l.startswith('DEBUG') 
                  and not l.startswith('INFO') and not l.startswith('BOT')
                  and not l.startswith('[SQUAD') and not l.startswith('WARNING')]
        print("\n".join(linhas).encode('ascii', 'replace').decode('ascii'))

    finally:
        ssh.close()

if __name__ == "__main__":
    run()
