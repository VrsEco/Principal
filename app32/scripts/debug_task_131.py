
import sys
import os
sys.path.append(os.getcwd())

from app import create_app
from models import db, Company, ProjectTask, ProcessInstance, Project, Employee

app = create_app()

def debug():
    with app.app_context():
        # Get task 131
        task = ProjectTask.query.get(131)
        if task:
            project = task.project
            company = project.company if project else None
            print(f"Task 131: {task.what}")
            if project:
                print(f"Project 16: {project.name}, Company ID: {project.company_id}")
            if company:
                print(f"Company: {company.name}, Is Active: {company.is_active}")
            print(f"Employee ID on task: {task.employee_id}")
            print(f"Task Status: {task.status}")
        else:
            print("Task 131 not found")

if __name__ == "__main__":
    debug()
