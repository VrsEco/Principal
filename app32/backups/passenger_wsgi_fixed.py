import sys
import os

# Base directory for the application
BASE_DIR = '/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/www'
VENV_PATH = '/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/.virtualenv/3.12/lib/python3.12/site-packages'

# Add the virtualenv site-packages
if VENV_PATH not in sys.path:
    sys.path.insert(0, VENV_PATH)

# Add the app32 directory to the path
APP32_DIR = os.path.join(BASE_DIR, 'app32')
if APP32_DIR not in sys.path:
    sys.path.insert(0, APP32_DIR)

# Add the www directory to the path
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Set environment variables
os.environ['FLASK_ENV'] = 'production'

try:
    from app import create_app
    application = create_app('production')
except Exception as e:
    with open(os.path.join(BASE_DIR, 'error_trace.txt'), 'a') as f:
        import traceback
        f.write("\n\n--- ERROR AT STARTUP ---\n")
        traceback.print_exc(file=f)
    raise
