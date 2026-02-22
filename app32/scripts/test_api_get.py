import sys
import os
sys.path.insert(0, os.getcwd())
from app import create_app
from models import db, User
from flask import session

app = create_app('testing')
client = app.test_client()

with app.app_context():
    # Force a company ID session variable if needed, but our GET should use request.args
    # We need to simulate a logged in user if permission_required is active
    user = User.query.filter_by(role='admin').first()
    
    with client.session_transaction() as sess:
        sess['active_company_id'] = 5
        # We also need flask_login to think we are logged in
        # Since we can't easily do it here with Flask-Login without more setup, 
        # let's try to bypass if possible or use a real request with login
        pass

    # Actually, permission_required uses current_user
    # Let's mock a login
    from flask_login import login_user
    with app.test_request_context():
        login_user(user)
        # Now call the API logic directly or via client if we can keep the context
        from api.resources.process import ProcessAreaListResource
        # Mocking request for get_request_company_id
        from flask import request
        with app.test_request_context('/api/process-areas?company_id=5'):
            res = ProcessAreaListResource().get()
            print(res)
