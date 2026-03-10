
import paramiko
import os

def final_deploy():
    host = "ip-69-164-205-75.cloudezapp.io"
    port = 22122
    user = "app"
    passw = "*Paraiso1978"
    
    app_path = "/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/www/app32"
    wsgi_path = "/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/www"
    python_path = "/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/.virtualenv/3.12/bin/python"
    venv_site = "/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/.virtualenv/3.12/lib/python3.12/site-packages"

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, port, user, passw)
    print(f"📡 Conectado como {user}")

    # 1. Update code
    print("🚀 Sincronizando repositório...")
    commands = [
        f"cd {app_path} && git fetch origin main",
        f"cd {app_path} && git reset --hard origin/main",
        f"cd {app_path} && git clean -fd",
    ]
    for cmd in commands:
        stdin, stdout, stderr = ssh.exec_command(cmd)
        print(stdout.read().decode())
        print(stderr.read().decode())

    # 2. Restore passenger_wsgi.py if it's a stub
    print("🛠️ Restaurando passenger_wsgi.py...")
    restore_cmd = f"cp {wsgi_path}/passenger_wsgi.py.bak {wsgi_path}/passenger_wsgi.py"
    ssh.exec_command(restore_cmd)

    # 3. Migration
    print("🗄️ Executando migração...")
    migrate_script = f"""
import sys, os
VENV_SITE = '{venv_site}'
if VENV_SITE not in sys.path:
    sys.path.insert(0, VENV_SITE)
sys.path.insert(0, '{app_path}')
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
    with sftp.file("/tmp/final_migrate.py", "w") as f:
        f.write(migrate_script)
    sftp.close()

    stdin, stdout, stderr = ssh.exec_command(f"{python_path} /tmp/final_migrate.py")
    out = stdout.read().decode()
    err = stderr.read().decode()
    print(out)
    print(err)

    if "MIGRATION_SUCCESS" in out:
        print("✅ Migração concluída com sucesso!")
    else:
        print("⚠️ Falha na migração (ou já estava em dia). Verifique logs.")

    # 4. Restart
    print("🔄 Reiniciando servidor...")
    ssh.exec_command(f"touch {wsgi_path}/restart.txt")
    ssh.exec_command(f"touch {wsgi_path}/passenger_wsgi.py")

    ssh.close()
    print("🎉 DEPLOY FINALIZADO!")

if __name__ == "__main__":
    final_deploy()
