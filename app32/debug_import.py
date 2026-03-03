import sys
import os
sys.path.insert(0, '/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/www/app32')
try:
    from app import create_app
    print("IMPORT SUCCESS")
except Exception as e:
    import traceback
    traceback.print_exc()
