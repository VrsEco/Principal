
import os
import sys
from app import create_app

print("Testing app creation in PRODUCTION mode...")
try:
    os.environ['TELEGRAM_SETUP_WEBHOOK'] = 'false'
    app = create_app('production')
    print("✅ App created successfully in production mode.")
except Exception as e:
    print(f"❌ FAILED to create app in production mode: {e}")
    import traceback
    traceback.print_exc()
