import sys
import os

sys.path.insert(0, '/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/www/app32')
sys.path.insert(0, '/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/.virtualenv/3.12/lib/python3.12/site-packages')
sys.path.insert(0, '/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/www')

os.environ['FLASK_ENV'] = 'production'

try:
    print("Testing app creation and import...")
    from app import create_app
    app = create_app('production')
    print("App created successfully.")
    
    with app.app_context():
        from models.user import User
        count = User.query.count()
        print(f"User count in DB: {count}")

except Exception as e:
    import traceback
    traceback.print_exc()
    sys.exit(1)
