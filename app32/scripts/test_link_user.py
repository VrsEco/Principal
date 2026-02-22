import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import app
from models import db, Employee, User, Company

with app.app_context():
    from flask import url_for
    with app.test_client() as client:
        admin = User.query.filter_by(role='admin').first()
        company = Company.query.first()
        if not company:
            company = Company(name="Test Link Company", client_code="TLC1")
            db.session.add(company)
            db.session.commit()
            
        with client.session_transaction() as sess:
            sess['_user_id'] = str(admin.id)
            sess['_fresh'] = True
            
        # create employee without user_id
        emp_name = "User Link Test Emp"
        emp = Employee(company_id=company.id, name=emp_name, status="active")
        db.session.add(emp)
        db.session.commit()
        emp_id = emp.id
        print(f"Created Employee #{emp.id} with name {emp.name}, user_id=None")
        
        # Link user by hitting the endpoint
        payload = {
            "name": emp_name,
            "email": "link.test.emp@versus.local",
            "role": "collaborator"
        }
        res = client.post(f"/api/companies/{company.id}/users", json=payload)
        res_data = res.get_json()
        print(f"POST Response: {res.status_code} - {res_data}")
        
        # Check if the employee was reused
        check_emp = Employee.query.get(emp_id)
        print(f"Checked Employee #{check_emp.id}, user_id={check_emp.user_id}, email={check_emp.email}")
        
        if str(res_data.get('id')) == str(emp_id):
            print("SUCCESS! Employee was reused.")
        else:
            print("FAILED! Different employee was created.")
            
        # Clean up
        u = User.query.filter_by(email="link.test.emp@versus.local").first()
        if u:
            # First remove employees
            for e in Employee.query.filter_by(user_id=u.id):
                db.session.delete(e)
            db.session.delete(u)
        else:
            db.session.delete(check_emp)
        
        db.session.commit()
