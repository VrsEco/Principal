
import sys
import os
sys.path.append(os.getcwd())

from app import create_app
from models import db, Company, ProjectTask, ProcessInstance, Project, Employee
from datetime import date, datetime, timedelta

app = create_app()

def reproduce():
    with app.app_context():
        with open('scripts/repro_log.txt', 'w', encoding='utf-8') as f:
            # 1. Setup
            f.write("--- Setup ---\n")
            
            # Find or create inactive company
            target_inactive = Company.query.filter_by(is_active=False).first()
            if not target_inactive:
                target_inactive = Company(name="REPRO INACTIVE CO", is_active=False)
                db.session.add(target_inactive)
                db.session.commit()
            f.write(f"Inactive Company: {target_inactive.name} (ID: {target_inactive.id})\n")

            # Create project for it
            test_project = Project.query.filter_by(company_id=target_inactive.id).first()
            if not test_project:
                test_project = Project(name="Repro Project", company_id=target_inactive.id)
                db.session.add(test_project)
                db.session.commit()
            f.write(f"Project: {test_project.name} (ID: {test_project.id}) for company {target_inactive.id}\n")

            # Find an employee
            emp = Employee.query.first()
            if not emp:
                f.write("No employees found!\n")
                return
            f.write(f"Using Employee: {emp.name} (ID: {emp.id})\n")

            # Create task
            test_task = ProjectTask(
                project_id=test_project.id,
                what="REPRO BUG TASK",
                employee_id=emp.id,
                status="planned",
                due_date=date.today()
            )
            db.session.add(test_task)
            db.session.commit()
            f.write(f"Task created: {test_task.what} (ID: {test_task.id}) for employee {emp.id}\n")

            # 2. Simulation
            f.write("\n--- Simulation ---\n")
            employee_ids = [emp.id]
            
            # This is exactly what auth.py does
            tasks = ProjectTask.query.filter(
                ProjectTask.employee_id.in_(employee_ids),
                ProjectTask.status.notin_(['completed', 'done', 'cancelled'])
            ).all()

            found_bug = False
            for t in tasks:
                comp = Company.query.get(t.project.company_id)
                f.write(f"Task ID: {t.id}, What: {t.what}, Company: {comp.name}, Active: {comp.is_active}\n")
                if t.id == test_task.id and not comp.is_active:
                    found_bug = True
            
            if found_bug:
                f.write("\nRESULT: Bug Reproduced! Task from inactive company is visible.\n")
            else:
                f.write("\nRESULT: Bug NOT reproduced. Task not found in list.\n")
                # Debug why not found
                all_tasks_for_emp = ProjectTask.query.filter_by(employee_id=emp.id).all()
                f.write(f"All tasks for emp {emp.id}: {[t.id for t in all_tasks_for_emp]}\n")
                f.write(f"Target task status: {test_task.status}\n")

if __name__ == "__main__":
    reproduce()
