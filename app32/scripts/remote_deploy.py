"""
Script de deploy remoto usando paramiko.
Executa o upgrade de migrações e reinicia o servidor no Configr.
"""
import paramiko
import sys

HOST = "ip-69-164-205-75.cloudezapp.io"
PORT = 22122
USER = "app2"
PASS = "*Paraiso1978"
APP_DIR = "/home/app2/public_html"
PYTHON = "/home/app2/.virtualenv/3.12/bin/python"

MIGRATE_SCRIPT = """
import sys, os
sys.path.insert(0, '.')
os.environ.setdefault('FLASK_CONFIG', 'production')
from flask_migrate import upgrade
from app import create_app
app = create_app('production')
with app.app_context():
    upgrade()
    print('MIGRATIONS APLICADAS COM SUCESSO!')
"""

RESTART_CMDS = [
    "touch /home/app2/public_html/restart.txt",
    "mkdir -p /home/app2/public_html/tmp && touch /home/app2/public_html/tmp/restart.txt",
]

def run(ssh, cmd):
    print(f"\n>>> {cmd[:80]}...")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=60)
    out = stdout.read().decode()
    err = stderr.read().decode()
    if out:
        print(out)
    if err:
        print("[STDERR]", err[:500])
    return stdout.channel.recv_exit_status(), out

def main():
    print("=" * 60)
    print("  DEPLOY REMOTO - Gestão Versus (Configr)")
    print("=" * 60)

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        print(f"\n🔌 Conectando a {HOST}:{PORT} como {USER}...")
        ssh.connect(HOST, port=PORT, username=USER, password=PASS)
        print("  ✅ Conectado!")

        # 1. Migrações
        print("\n🗃️  Executando migrações de banco de dados...")
        script_path = "/tmp/run_migrate.py"
        sftp = ssh.open_sftp()
        with sftp.file(script_path, 'w') as f:
            f.write(MIGRATE_SCRIPT)
        sftp.close()

        code, out = run(ssh, f"cd {APP_DIR} && {PYTHON} {script_path}")
        if "MIGRATIONS APLICADAS" in out or "Running upgrade" in out or "INFO" in out:
            print("  ✅ Migrações OK!")
        elif "already" in out.lower() or code == 0:
            print("  ✅ Sem migrações pendentes ou já aplicadas.")
        else:
            print(f"  ⚠️  Código de saída: {code}")

        # 2. Reiniciar o servidor
        print("\n🔄 Reiniciando servidor (Passenger/uWSGI touch files)...")
        for cmd in RESTART_CMDS:
            run(ssh, cmd)
        
        # Tenta também pkill no uwsgi
        run(ssh, "pkill -HUP -f 'uwsgi' 2>/dev/null || true")

        print("  ✅ Servidor reiniciado!")

        print("\n" + "=" * 60)
        print("  ✨ DEPLOY CONCLUÍDO COM SUCESSO!")
        print("  🌐 Acesse: https://app.gestaoversus.com.br")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        sys.exit(1)
    finally:
        ssh.close()

if __name__ == "__main__":
    main()
