
import os
import sys

# Add root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))


from app import create_app
from models import db
from models.project import ProjectTask
from models.process import ProcessInstance

def find_activity(search_term):
    app = create_app()
    with app.app_context():
        # Search in ProjectTask
        tasks = ProjectTask.query.filter(ProjectTask.what.ilike(f"%{search_term}%")).all()
        for t in tasks:
            print(f"TYPE: project_task | ID: {t.id} | NAME: {t.what} | COMPANY_ID: {t.project.company_id if t.project else 'N/A'}")
        
        # Search in ProcessInstance
        instances = ProcessInstance.query.filter(ProcessInstance.title.ilike(f"%{search_term}%")).all()
        for i in instances:
            print(f"TYPE: process_instance | ID: {i.id} | NAME: {i.title} | COMPANY_ID: {i.company_id}")

if __name__ == "__main__":
    search = "asd df a"
    if len(sys.argv) > 1:
        search = sys.argv[1]
    find_activity(search)

