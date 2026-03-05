import sys
import os

sys.path.append('/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/www/app32')

from app import create_app
from models import Company, ProjectTask, ProcessInstance

app = create_app('production')

with app.app_context():
    c = Company.query.filter(Company.name.ilike('%Eua%Moveis%')).first()
    if c:
        print(f"Company: {c.name} (ID: {c.id}), is_active: {c.is_active}")
        tasks = ProjectTask.query.filter(ProjectTask.project.has(company_id=c.id)).all()
        print(f"Tasks count: {len(tasks)}")
        for t in tasks:
            print(f"  Task {t.id}: {t.what} | status {t.status} | emp {t.employee_id}")
    else:
        print("Company not found")
