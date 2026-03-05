
import sys
import os
sys.path.append(os.getcwd())

from app import create_app
from models import db, Company, ProjectTask, ProcessInstance, Project, Employee, User
from api.routes.auth import auth_bp
from flask import render_template

app = create_app()

def test_portal():
    with app.test_client() as client:
        with app.app_context():
            # Get an employee
            emp = None
            for e in Employee.query.all():
                if e.user_id:
                    emp = e
                    break
            
            if not emp:
                print("No employees to test.")
                return

            # Login as the user of this employee
            user = User.query.get(emp.user_id)
            if not user:
                print("Employee has no user.")
                return

            print(f"Logging in as {user.email}")
            with client.session_transaction() as sess:
                sess['_user_id'] = str(user.id)
                sess['_id'] = "random_session_id"
                sess['_fresh'] = True

            # Request /portal
            print("Requesting /portal...")
            response = client.get('/portal')
            print(f"Status: {response.status_code}")
            
            # See if there's any crash in the rendered HTML
            # Check length to ensure it rendered
            html = response.get_data(as_text=True)
            print(f"Response HTML length: {len(html)}")
            
            # Verify if "REPRO BUG TASK" is missing (inactive company)
            if "REPRO BUG TASK" in html:
                print("FAILED: REPRO BUG TASK is still in the portal output!")
            else:
                print("SUCCESS: REPRO BUG TASK from inactive company was filtered out.")

if __name__ == "__main__":
    test_portal()
