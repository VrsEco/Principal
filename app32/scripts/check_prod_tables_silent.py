
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
    # Hack to suppress prints during import
    sys.stdout = open(os.devnull, 'w')
    from app import create_app
    from models import db
    from sqlalchemy import inspect
    app = create_app('production')
    # Restore stdout
    sys.stdout = sys.__stdout__
    with app.app_context():
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        if 'project_task_dependencies' in tables:
            print("FOUND_TABLE_DEPENDENCIES=TRUE")
        else:
            print("FOUND_TABLE_DEPENDENCIES=FALSE")
        # Also print some common tables to verify it worked
        print("TABLES_COUNT:", len(tables))
except Exception as e:
    sys.stdout = sys.__stdout__
    print(f"ERROR: {e}")
"""
    sftp = ssh.open_sftp()
    with sftp.file("/tmp/check_tables_silent.py", "w") as f:
        f.write(check_script)
    sftp.close()

    stdin, stdout, stderr = ssh.exec_command("/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/.virtualenv/3.12/bin/python /tmp/check_tables_silent.py")
    print(stdout.read().decode())
    print(stderr.read().decode())
    ssh.close()

if __name__ == "__main__":
    check_tables()
