import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import app
from models.user import User

with app.app_context():
    from flask import url_for
    
    with app.test_client() as client:
        admin = User.query.filter_by(role='admin').first()
        with client.session_transaction() as sess:
            sess['_user_id'] = str(admin.id)
            sess['_fresh'] = True
        
        response = client.get('/my-work/api/activities?scope=me')
        data = response.get_json()
        
        activities = data.get('data', [])
        print(f"Total Activities: {len(activities)}")
        if activities:
            print("First 5 activities:")
            for i, act in enumerate(activities[:5]):
                print(f"[{i}] ID: {act.get('id')}, Type: {act.get('type')}, C_ID: {act.get('company_id')}, Title: {act.get('title')}")
