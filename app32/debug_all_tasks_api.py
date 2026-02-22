import json
from app import app
from api.resources.project_task import ProjectAllTasksResource
from flask import session

def test_all_tasks():
    with app.app_context():
        # We need to simulate a request or at least set company_id
        with app.test_request_context():
            # Set session if needed or mock get_request_company_id
            session['active_company_id'] = 5 # Assuming company 5 as in logs
            resource = ProjectAllTasksResource()
            response, code = resource.get()
            print(f"Status Code: {code}")
            print(f"Data: {json.dumps(response, indent=2)}")

if __name__ == "__main__":
    test_all_tasks()
