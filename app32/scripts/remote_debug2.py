import sys
import os

sys.path.append('/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/www/app32')

from app import create_app
from models import Company, ProjectTask, ProcessInstance, Project, Employee
from sqlalchemy.orm import joinedload

app = create_app('production')

with app.app_context():
    employee_ids = [24]
    tasks = ProjectTask.query.join(Project).join(Company).filter(
        ProjectTask.employee_id.in_(employee_ids),
        ProjectTask.status.notin_(['completed', 'done', 'cancelled']),
        Company.is_active == True
    ).options(joinedload(ProjectTask.project)).all()
    
    print(f"Tasks for employee[s] {employee_ids}: {len(tasks)}")
    for t in tasks:
        print(f"  Task {t.id}: {t.what} | status {t.status} | emp {t.employee_id} | proj {t.project.id} | comp {t.project.company.id} | is_active {t.project.company.is_active}")
