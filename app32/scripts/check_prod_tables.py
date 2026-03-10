
import paramiko

def check_tables():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect("ip-69-164-205-75.cloudezapp.io", port=22122, username="app", password="*Paraiso1978")
    
    check_script = """
import sys, os
VENV_SITE = '/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/.virtualenv/3.12/lib/python3.12/site-packages'
if VENV_SITE not in sys.path:
    sys.path.insert(0, VENV_SITE)
sys.path.insert(0, '/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/www/app32')
os.environ.setdefault('FLASK_CONFIG', 'production')
try:
    from app import create_app
    from models import db
    from sqlalchemy import inspect
    app = create_app('production')
    with app.app_context():
        inspector = inspect(db.engine)
        print("TABLES:", inspector.get_table_names())
except Exception as e:
    import traceback
    traceback.print_exc()
"""
    sftp = ssh.open_sftp()
    with sftp.file("/tmp/check_tables.py", "w") as f:
        f.write(check_script)
    sftp.close()

    stdin, stdout, stderr = ssh.exec_command("/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/.virtualenv/3.12/bin/python /tmp/check_tables.py")
    print(stdout.read().decode())
    print(stderr.read().decode())
    ssh.close()

if __name__ == "__main__":
    check_tables()
