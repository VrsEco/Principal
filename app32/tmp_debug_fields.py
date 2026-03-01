
import sys
import os
from flask import Flask

# Set up the app context
sys.path.insert(0, os.getcwd())
from app import create_app
from models.user import User
from services.my_work.discovery_service import get_user_activities_v2
from database.config_database import db

app = create_app()

with app.app_context():
    # User mff2000@gmail.com is likely id 3 or similar
    user = User.query.filter_by(email='mff2000@gmail.com').first()
    if not user:
        print("User not found")
        sys.exit(1)
    
    print(f"Debug for user: {user.email} (id={user.id})")
    
    activities, counts = get_user_activities_v2(user.id, scope='general')
    
    print(f"Counts: {counts}")
    if activities:
        act = activities[0]
        print("Example activity keys with values:")
        for k in ['id', 'title', 'type', 'estimated_hours', 'worked_hours', 'status', 'company_id']:
            print(f"  {k}: {act.get(k)}")
        
        # Check all keys of first activity
        print(f"All keys: {list(act.keys())}")
    else:
        print("No activities found")
