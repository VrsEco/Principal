import sys
import os
import traceback

sys.path.insert(0, '/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/www/app32')
sys.path.insert(0, '/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/.virtualenv/3.12/lib/python3.12/site-packages')
sys.path.insert(0, '/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/www')

os.environ['FLASK_ENV'] = 'production'

print("STARTING TEST SCRIPT", flush=True)

try:
    print("Importing app modules...", flush=True)
    from app import create_app
    print("Calling create_app...", flush=True)
    app = create_app('production')
    app.config['SCHEDULER_API_ENABLED'] = False
    app.config['TESTING'] = True # Propagate exceptions
    print("App created successfully!", flush=True)
    
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['company_id'] = 1
        
        try:
            print("Trying to GET /...", flush=True)
            res = client.get('/')
            print(f"Status code for /: {res.status_code}", flush=True)
            if res.status_code == 500:
                print(f"500 Output /: {res.data.decode('utf-8')}", flush=True)
                
            print("Trying to GET /login...", flush=True)
            res2 = client.get('/login')
            print(f"Status code for /login: {res2.status_code}", flush=True)
            if res2.status_code == 500:
                print(f"500 Output /login: {res2.data.decode('utf-8')}", flush=True)
                
        except Exception as inner_e:
            with open("/home/app/real_error.txt", "w") as ef:
                traceback.print_exc(file=ef)
            print("INNER EXCEPTION CAUGHT", flush=True)
            
except Exception as e:
    with open("/home/app/real_error.txt", "w") as ef:
        traceback.print_exc(file=ef)
    print("OUTER EXCEPTION CAUGHT", flush=True)

print("FINISHING SCRIPTS", flush=True)
import os
os._exit(0)
