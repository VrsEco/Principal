import sys
import os
import traceback

sys.path.insert(0, '/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/www/app32')
sys.path.insert(0, '/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/.virtualenv/3.12/lib/python3.12/site-packages')
sys.path.insert(0, '/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/www')

os.environ['FLASK_ENV'] = 'production'

try:
    from app import create_app
    app = create_app('production')
    app.config['SCHEDULER_API_ENABLED'] = False
    
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['company_id'] = 1
        
        print("Testing /dashboard...")
        app.config['PROPAGATE_EXCEPTIONS'] = True # So exceptions are raised, not just 500 page
        response = client.get('/dashboard')
        print(f"Status Code: {response.status_code}")
except Exception as e:
    print("EXCEPTION CAUGHT:")
    traceback.print_exc()

os._exit(0)
