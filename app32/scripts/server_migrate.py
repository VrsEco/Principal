
import sys, os
# Add the site-packages discovered in passenger_wsgi.py
VENV_SITE = '/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/.virtualenv/3.12/lib/python3.12/site-packages'
if VENV_SITE not in sys.path:
    sys.path.insert(0, VENV_SITE)
sys.path.insert(0, '/home/app2/public_html/app32')

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
