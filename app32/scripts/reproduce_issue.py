
import sys
import os
from flask import Flask
from flask.testing import FlaskClient

# Add the application directory to the python path
sys.path.append(os.getcwd())

try:
    from app_pev import app
    from models import db
    from models.user import User
except ImportError as e:
    print(f"Error importing app: {e}")
    sys.exit(1)

def check_api():
    with app.test_client() as client:
        with app.app_context():
            # Mock login (if necessary, or just use a user that exists)
            # Assuming user ID 1 exists and has access
            user = User.query.filter_by(email='mff2000@gmail.com').first()
            if not user:
                print("User mff2000@gmail.com not found")
                return

            # We might need to login. 
            # Since we can't easily mock login_required without a session, 
            # we'll try to use login_user if flask_login is set up, 
            # or just bypass if possible. 
            # But usually test_client needs a session.
            
            # Let's try to login via the login route if it exists, or manually set session
            with client.session_transaction() as sess:
                sess['_user_id'] = str(user.id)
                sess['_fresh'] = True

            # Fetch the API
            response = client.get('/api/companies/13/process-instances')
            
            if response.status_code == 404:
                print("Route not found: /api/companies/13/process-instances")
                # Try with underscore
                response = client.get('/api/companies/13/process_instances')
                if response.status_code == 404:
                     print("Route not found: /api/companies/13/process_instances")
            
            if response.status_code == 200:
                data = response.get_json()
                print("Response Data (First Item):")
                if data and isinstance(data, list) and len(data) > 0:
                    print(data[0])
                    # Check for hours
                    item = data[0]
                    print(f"Estimated Hours: {item.get('estimated_hours')}")
                    print(f"Actual Hours: {item.get('actual_hours')}")
                    print(f"Worked Hours: {item.get('worked_hours')}")
                elif data and isinstance(data, dict) and 'data' in data:
                     items = data['data']
                     if items and len(items) > 0:
                        print(items[0])
                        item = items[0]
                        print(f"Estimated Hours: {item.get('estimated_hours')}")
                        print(f"Actual Hours: {item.get('actual_hours')}")
                        print(f"Worked Hours: {item.get('worked_hours')}")
                else:
                    print("No data or unexpected format")
            else:
                print(f"Error: {response.status_code}")
                print(response.data)

if __name__ == "__main__":
    check_api()
