
import traceback
import os
import sys

sys.path.append(os.getcwd())

try:
    from app import create_app
    from flask_login import login_user
    
    app = create_app('development')
    app.debug = True
    app.config['PRESERVE_CONTEXT_ON_EXCEPTION'] = False
    
    with app.app_context():
        # Get first user from DB
        from models import User
        user = User.query.first()
        if not user:
            print("No user found in DB!")
        else:
            print(f"Using user: {user.email} (id={user.id})")
        
        with app.test_client() as client:
            # Force login directly via login_user inside a request context
            with client.application.test_request_context('/'):
                if user:
                    login_user(user)
            
            # Set session manually
            with client.session_transaction() as sess:
                sess['_user_id'] = str(user.id) if user else '1'
                sess['_fresh'] = True
                sess['active_company_id'] = 1
                print("Set session:", dict(sess))
            
            # Step: GET /incentives
            print("\nSimulating GET /incentives...")
            resp = client.get('/incentives', follow_redirects=False)
            print(f"Status Code: {resp.status_code}")
            print(f"Location: {resp.headers.get('Location', 'No redirect')}")
            if resp.status_code == 500:
                print("ERROR 500 detected.")
                html = resp.data.decode('utf-8', errors='replace')
                # Find traceback in the error page
                if 'Traceback' in html:
                    start = html.find('Traceback')
                    print(html[start:start+3000])
                else:
                    print(html[:3000])
            elif resp.status_code == 200:
                print("SUCCESS! Dashboard loaded, length:", len(resp.data))

except Exception:
    traceback.print_exc()
