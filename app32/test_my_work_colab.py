from app import create_app
from models.user import User
from models.employee import Employee
from models import db
import json

app = create_app()

with app.test_client() as client:
    with app.app_context():
        # Find a colaborador by role='user'
        user = User.query.filter_by(role='user').first()
        if not user:
            print("No user found with role='user'")
            exit()
        emp = Employee.query.filter_by(user_id=user.id).first()
        print(f"Testing with user: {user.email}, role: {user.role}, company: {emp.company_id if emp else None}")

        with client.session_transaction() as sess:
            sess['_user_id'] = str(user.id)
            sess['_fresh'] = True
            if emp:
                sess['active_company_id'] = emp.company_id
        
        try:
            res = client.get('/my-work/api/activities?scope=company', follow_redirects=True)
            print("Status Code:", res.status_code)
            data = json.loads(res.get_data(as_text=True))
            acts = data.get("data", [])
            print(f"Returned {len(acts)} activities in 'company' scope.")
            # Check if any is NOT mine
            not_mine = 0
            for a in acts:
                if not a.get("viewer_is_directly_assigned"):
                    not_mine += 1
            print(f"Activities NOT assigned to user: {not_mine}")
            print("Scopes:", data.get("scope_counts"))
        except Exception as e:
            import traceback
            traceback.print_exc()
