
import sys, os
sys.path.insert(0, os.path.abspath('.'))
from app import app
from models import ProjectTask, Employee
with app.app_context():
    task = ProjectTask.query.get(71)
    if task:
        emp = Employee.query.get(task.employee_id)
        print(f"Task {task.id} responsible: E{task.employee_id} ({emp.name if emp else 'None'}), Linked User: {emp.user_id if emp else 'None'}")
    else:
        print("Task 71 not found")
