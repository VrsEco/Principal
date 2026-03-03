import sys
import os

# Path to the real app
BASE_DIR = '/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/www/app32'
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

def get_wsgi_application():
    from app import create_app
    return create_app('production')
