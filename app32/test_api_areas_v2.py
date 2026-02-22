
from app import create_app
from models import db, User, Company
from flask_login import login_user
import json

app = create_app()
with app.test_request_context():
    with app.app_context():
        client = app.test_client()
        
        # Encontrar um admin
        admin = User.query.filter_by(role='admin').first()
        if not admin:
            # Se não tiver admin, criar um temporário? Ou pegar qualquer um
            admin = User.query.first()
            if admin:
                admin.role = 'admin'
                db.session.commit()
        
        if not admin:
            print("No users found in database.")
            exit(1)
            
        print(f"Testing as user: {admin.email} (Role: {admin.role})")
        
        # Login
        with client.session_transaction() as sess:
            sess['_user_id'] = str(admin.id)
            sess['active_company_id'] = 5
        
        # Test API
        response = client.get('/api/process-areas?company_id=5')
        print(f"Status Code: {response.status_code}")
        try:
            data = response.get_json()
            print(f"Areas Data: {json.dumps(data, indent=2)}")
        except:
            print(f"Raw Output: {response.data.decode('utf-8')}")

        # Test Macros too
        response = client.get('/api/macro-processes?company_id=5')
        print(f"Macros Status Code: {response.status_code}")
        
        # Test Processes too
        response = client.get('/api/processes?company_id=5')
        print(f"Processes Status Code: {response.status_code}")
