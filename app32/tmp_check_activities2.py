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
    user = User.query.filter_by(email="mff2000@gmail.com").first()
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
    
    print(f"Me scope: user_id={user.id}")
    print(f"counts result: {scope_counts}")
    print(f"Total length returned activities list: {len(activities)}")
    if len(activities) > 0:
      print("First one:")
      print(activities[0].get("id"), activities[0].get("title"))

    # Also test with 'general' scope
    activities2, counts2 = get_user_activities_v2(
        user_id=user.id,
        scope='general',
        filters={},
        company_ids=None,
        active_company_id=None
    )
    print(f"General scope total length activities list: {len(activities2)}")

