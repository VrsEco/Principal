from app import create_app
from models import Role, db

app = create_app()
with app.app_context():
    roles = Role.query.all()
    count = 0
    for r in roles:
        if not r.permissions:
            r.permissions = {}
        
        projects_perms = r.permissions.get('projects', [])
        modified = False
        
        if 'view' not in projects_perms:
            projects_perms.append('view')
            modified = True
        if 'create' not in projects_perms:
            projects_perms.append('create')
            modified = True
        if 'edit' not in projects_perms:
            projects_perms.append('edit')
            modified = True
            
        if modified:
            r.permissions['projects'] = projects_perms
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(r, 'permissions')
            count += 1
            
    db.session.commit()
    print(f'PRODUCTION DB PATCH: Updated {count} roles with view/create/edit permissions for projects.')
