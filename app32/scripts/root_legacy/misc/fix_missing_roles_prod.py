import sys
sys.path.insert(0, '.')
from app import create_app
from models import db, Role
from models.employee import Employee
from sqlalchemy.orm.attributes import flag_modified

app = create_app()
with app.app_context():
    # Find employees without role that have user_id and are active
    orphan_emps = Employee.query.filter(
        Employee.role_id == None,
        Employee.user_id != None,
        Employee.status == 'active'
    ).all()
    
    print(f'Employees without role but with active user: {len(orphan_emps)}')
    
    fixed = 0
    for emp in orphan_emps:
        # Find or create a default "Colaborador" role for the company
        role = Role.query.filter_by(company_id=emp.company_id).first()
        if not role:
            # Create a minimal role
            role = Role(
                company_id=emp.company_id,
                title='Colaborador',
                permissions={
                    'projects': ['view', 'create', 'edit'],
                    'my_work': ['view'],
                    'routines': ['view'],
                }
            )
            db.session.add(role)
            db.session.flush()
            print(f'  Created new Colaborador role for company {emp.company_id}')
        else:
            # Ensure the role has projects view
            if not role.permissions:
                role.permissions = {}
            perms = role.permissions.get('projects', [])
            changed = False
            for p in ['view', 'create', 'edit']:
                if p not in perms:
                    perms.append(p)
                    changed = True
            if changed:
                role.permissions['projects'] = perms
                flag_modified(role, 'permissions')
        
        emp.role_id = role.id
        print(f'  Assigned role {role.id} ({role.title}) to Employee {emp.id} (User: {emp.user_id}) company {emp.company_id}')
        fixed += 1
    
    db.session.commit()
    print(f'\nFIXED {fixed} employees without role in PRODUCTION.')
