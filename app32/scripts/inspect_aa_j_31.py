
import os, sys
sys.path.append(os.getcwd())
from app import create_app
from models import db, ProjectTask, Project

app = create_app()
with app.app_context():
    p = Project.query.filter_by(id=31).first()
    if p:
        print(f"Project ID 31: {p.code} - {p.name}")
    else:
        # Try finding by code
        p = Project.query.filter(Project.code.ilike('AA.J.31%')).first()
        if p:
            print(f"Project found by code: {p.id} | {p.code} - {p.name}")
        else:
            print("Project AA.J.31 not found.")
            sys.exit(0)
    
    tasks = ProjectTask.query.filter_by(project_id=p.id).all()
    print(f"Found {len(tasks)} tasks:")
    for t in tasks:
        print(f"- ID: {t.id} | Status: {t.status} | What: {t.what}")
