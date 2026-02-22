import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import app
from models import db, Employee, User, Company

with app.app_context():
    from flask import url_for
    with app.test_client() as client:
        admin = User.query.filter_by(role='admin').first()
        company = Company.query.first()
            
        with client.session_transaction() as sess:
            sess['_user_id'] = str(admin.id)
            sess['_fresh'] = True
            
        print("Testing system-users GET...")
        res = client.get('/api/system-users')
        if res.status_code == 200:
            print("system-users OK, returned:", len(res.get_json()), "users")
        else:
            print("system-users ERR:", res.status_code)
            
        print("Testing unlinked-employees GET...")
        res = client.get(f'/api/companies/{company.id}/unlinked-employees')
        if res.status_code == 200:
            print("unlinked-employees OK, returned:", len(res.get_json()), "employees")
        else:
            print("unlinked-employees ERR:", res.status_code)

        print("Done.")
