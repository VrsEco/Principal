
from app import create_app
from models import db, Project, ProjectTask

app = create_app()
with app.app_context():
    projects = Project.query.all()
    print(f"Total projects: {len(projects)}")
    for p in projects:
        tasks = ProjectTask.query.filter_by(project_id=p.id).all()
        print(f"Project ID: {p.id} | Company ID: {p.company_id} | Name: {p.name} | Tasks: {len(tasks)}")
        for t in tasks:
            print(f"  -> Task ID: {t.id} | What: {t.what} | Stage: {t.stage}")
