
import sys, os
sys.path.insert(0, os.path.abspath('.'))
from app import app
from models import db
from sqlalchemy import text
with app.app_context():
    try:
        res = db.session.execute(text("SELECT id FROM process_instances WHERE company_id = 37")).fetchall()
        print(f"Process Instances (Company 37): {len(res)}")
        
        # Check collaborators
        res2 = db.session.execute(text("SELECT instance_id, employee_id FROM process_instance_collaborators")).fetchall()
        print(f"Total Collaborators linked: {len(res2)}")
    except Exception as e:
        print(f"Error: {e}")
