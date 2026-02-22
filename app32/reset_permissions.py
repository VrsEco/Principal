from app import create_app
from models import db, Role, User, Employee

app = create_app()
with app.app_context():
    # 1. Update all roles to have full permissions for processes and projects
    roles = Role.query.all()
    for role in roles:
        role.permissions = {
            "projects": ["view", "create", "edit", "delete"],
            "indicators": ["view", "create", "edit", "delete"],
            "processes": ["view", "create", "edit", "delete"],
            "companies": ["view", "create", "edit", "delete"],
            "okrs": ["view", "create", "edit", "delete"],
            "employees": ["view", "create", "edit", "delete"]
        }
        print(f"Updated permissions for role {role.id}: {role.title}")
    
    # 2. Also check if the current user is an admin globally
    # If they are 'collaborator' but not an employee of a company, it might be an issue too.
    
    db.session.commit()
    print("Database permissions reset complete.")
