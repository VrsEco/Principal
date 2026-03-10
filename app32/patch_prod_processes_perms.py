from app import create_app
from models import Role, db
from sqlalchemy.orm.attributes import flag_modified

app = create_app()
with app.app_context():
    roles = Role.query.all()
    count = 0
    for r in roles:
        if not r.permissions:
            r.permissions = {}
        
        proc_perms = r.permissions.get('processes', [])
        modified = False
        
        if 'view' not in proc_perms:
            proc_perms.append('view')
            modified = True
            
        if modified:
            r.permissions['processes'] = proc_perms
            flag_modified(r, 'permissions')
            count += 1
            
    db.session.commit()
    print(f'PRODUCTION DB PATCH: Updated {count} roles with view permission for processes.')
