import sys
sys.path.insert(0, '.')
from app import create_app
from models import db, User, Role
from models.employee import Employee

app = create_app()
with app.app_context():
    # Find users that are NOT admin
    non_admin = User.query.filter(User.role != 'admin').all()
    print(f'Total non-admin users: {len(non_admin)}')
    for u in non_admin:
        emps = Employee.query.filter_by(user_id=u.id).all()
        for e in emps:
            has_role = e.role_id is not None
            role_perms = None
            if e.role:
                role_perms = e.role.permissions.get('projects', []) if e.role.permissions else []
            print(f'  User: {u.id} | {u.name} | Employee: {e.id} | company: {e.company_id} | role_id: {e.role_id} | has_role: {has_role} | projects_perms: {role_perms} | status: {getattr(e, "status", "?")}')
