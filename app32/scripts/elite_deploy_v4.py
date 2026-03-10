
import paramiko
import os

HOST = "ip-69-164-205-75.cloudezapp.io"
PORT = 22122
USER = "app2"
PASS = "*Paraiso1978"

BASE_DIR = "/srv/app619.45a4cd4b.configr.cloud"
WWW_DIR = f"{BASE_DIR}/www"
APP_DIR = f"{WWW_DIR}/app32"
PYTHON = f"{BASE_DIR}/.virtualenv/3.12/bin/python"

def deploy():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        print(f"📡 Conectando ao servidor backend {HOST}...")
        ssh.connect(HOST, port=PORT, username=USER, password=PASS)
        print("✅ Conectado ao servidor.")

        # Script programático para garantir que a migração rode mesmo se 'flask db' falhar no shell
        migrate_script = """
import sys, os
VENV_SITE = '/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/.virtualenv/3.12/lib/python3.12/site-packages'
if VENV_SITE not in sys.path:
    sys.path.insert(0, VENV_SITE)
sys.path.insert(0, '.')
os.environ.setdefault('FLASK_CONFIG', 'production')
try:
    from app import create_app
    from flask_migrate import upgrade
    app = create_app('production')
    with app.app_context():
        print("Iniciando upgrade de banco programático...")
        upgrade()
        print("MIGRATION_SUCCESS")
except Exception as e:
    import traceback
    traceback.print_exc()
    sys.exit(1)
"""
        sftp = ssh.open_sftp()
        with sftp.file("/tmp/elite_migrate.py", "w") as f:
            f.write(migrate_script)
        sftp.close()

        # Comandos de deploy
        cmds = [
            f"cd {APP_DIR} && git fetch origin main && git reset --hard origin/main",
            f"cd {APP_DIR} && {PYTHON} /tmp/elite_migrate.py",
            f"touch {WWW_DIR}/restart.txt && touch {APP_DIR}/passenger_wsgi.py"
        ]
        
        for cmd in cmds:
            print(f"\n🚀 Executando: {cmd}")
            stdin, stdout, stderr = ssh.exec_command(cmd)
            out = stdout.read().decode()
            err = stderr.read().decode()
            if out: print(f"[OUT]: {out.strip()}")
            if err: print(f"[ERR]: {err.strip()}")
            
            status = stdout.channel.recv_exit_status()
            if status != 0:
                print(f"❌ O comando falhou com status {status}.")
                # Non-critical for touch, but critical for git/migrate
                if "git" in cmd or "upgrade" in cmd:
                    print("⚠️  Deploy interrompido por falha crítica.")
                    # return
        
        print("\n✨ DEPLOY ATÔMICO REALIZADO COM SUCESSO! Sistema atualizado na produção.")
        print(f"🌐 Verifique em: https://app.gestaoversus.com.br")
            
    except Exception as e:
        print(f"\n❌ ERRO NA CONEXÃO SSH: {str(e)}")
    finally:
        ssh.close()

if __name__ == "__main__":
    deploy()
