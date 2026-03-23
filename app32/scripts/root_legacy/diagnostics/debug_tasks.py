import requests
import json

def test_api():
    url = "http://127.0.0.1:5032/api/projects/5/tasks"
    try:
        # Assuming no auth required for localhost or can bypass if simple
        # But wait, the app is running in the background.
        # Let's try to query the DB directly to see if data exists
        import os
        from app import app
        from models import ProjectTask
        
        with app.app_context():
            tasks = ProjectTask.query.all()
            print(f"Total tasks: {len(tasks)}")
            for task in tasks:
                d = task.to_dict()
                print(f"Task ID: {d['id']}, What: {d['what']}, Emp ID: {d['employee_id']}, Emp Name: {d.get('employee_name')}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_api()
