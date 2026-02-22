import sys
import os
import json
sys.path.insert(0, os.getcwd())
from app import create_app
from models import db, User, ProcessArea
from flask import session

from app import app
# app is already created in app.py as app = create_app()

with app.app_context():
    from api.resources.process import ProcessAreaListResource
    from flask import request
    
    with app.test_request_context('/api/process-areas?company_id=1'):
        # Mocking current_user for permission_required 
        from flask_login import login_user
        user = User.query.filter_by(role='admin').first()
        login_user(user)
        
        res = ProcessAreaListResource().get()
        # res is (data, status_code)
        with open('api_response.json', 'w', encoding='utf-8') as f:
            json.dump(res[0], f, indent=2)
        print(f"Status Code: {res[1]}")
