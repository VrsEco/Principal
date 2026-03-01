import sys
import os

# Set up the app context
sys.path.insert(0, os.path.dirname(__file__))
from app import create_app
from models import db, User

app = create_app()

with app.app_context():
    from services.my_work.discovery_service import get_user_activities_v2
    # Find a user to test
    user = User.query.first()
    if not user:
        print("No user found")
        sys.exit(1)
        
    activities, scope_counts = get_user_activities_v2(
        user_id=user.id,
        scope='me',
        filters={},
        company_ids=None,
        active_company_id=None
    )
    
    import json
    # Let's inspect the first 3 activities' hours
    print("Found total:", len(activities))
    for act in activities[:3]:
        print({
            "id": act.get("id"),
            "title": act.get("title"),
            "estimated_hours": act.get("estimated_hours"),
            "worked_hours": act.get("worked_hours"),
            "type": act.get("type")
        })
