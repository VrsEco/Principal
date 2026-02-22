import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import app
from models.user import User

with app.app_context():
    from flask import url_for
    from app import app
    
    with app.test_client() as client:
        print("Login como admin...")
        admin = User.query.filter_by(role='admin').first()
        from flask_login import login_user
        
        @app.route('/test-login')
        def test_login():
            login_user(admin)
            return "ok"
            
        client.get('/test-login')
        
        print("Testando My Work API Call...")
        response = client.get('/my-work/api/activities?scope=me')
        print(f"Status Code API: {response.status_code}")
        
        data = response.get_json()
        print(f"Success: {data.get('success')}")
        
        if not data.get('success'):
            print(f"Error Message: {data.get('error')}")
        else:
            activities = data.get('data', [])
            print(f"Total Activities: {len(activities)}")
            
            stats = data.get('stats', {})
            print(f"Stats: {stats}")
