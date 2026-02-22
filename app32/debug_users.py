from app import create_app
from models import db, User, Employee, Role
from flask import session

app = create_app()
with app.app_context():
    users = User.query.all()
    for u in users:
        print(f"User: {u.email}, Role: {u.role}")
        emps = Employee.query.filter_by(user_id=u.id).all()
        for e in emps:
            role = Role.query.get(e.role_id)
            print(f"  Employee in Company {e.company_id}, Role: {role.title if role else 'None'}")
            if role:
                print(f"    Permissions: {role.permissions}")
