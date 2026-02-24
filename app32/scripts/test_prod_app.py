
import sys
import os

# Add app32 to sys.path
sys.path.insert(0, '/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/www/app32')

from app import create_app, db

try:
    print("Testing app creation...")
    app = create_app('production')
    print("App created successfully!")
    with app.app_context():
        # Check if we can connect to DB
        from models.user import User
        count = User.query.count()
        print(f"User count in DB: {count}")
except Exception as e:
    import traceback
    traceback.print_exc()
    sys.exit(1)
