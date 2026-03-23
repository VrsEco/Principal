import os
from app import create_app
from models import db
from models.user import User
from models.project import Project, ProjectTask

app = create_app('default')
with app.app_context():
    user = User.query.first()
    if user:
        print(f"User ID: {user.id}, Role: {user.role}")
    
    # Check tasks for company 5 (from user logs)
    tasks = ProjectTask.query.join(Project, ProjectTask.project_id == Project.id).filter(Project.company_id == 5).all()
    print(f"Found {len(tasks)} tasks for company 5")
    for t in tasks[:5]:
        print(f"Task: {t.what}, Project: {t.project.name if t.project else 'None'}")
