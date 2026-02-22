
import sys
import os
from sqlalchemy import text

sys.path.append(os.getcwd())
from app import create_app, db
from models import Plan, Project, Employee

app = create_app()

def inspect():
    with app.app_context():
        cid = 36
        print(f"--- INSPECTING TITAN (ID {cid}) ---")
        
        plans = Plan.query.filter_by(company_id=cid).all()
        print(f"PLANS ({len(plans)}):")
        for p in plans:
            print(f" - [{p.id}] {p.title} (Mode: {p.mode}) Created: {p.created_at}")
            
        projects = Project.query.filter_by(company_id=cid).all()
        print(f"PROJECTS ({len(projects)}):")
        for p in projects:
            print(f" - [{p.id}] {p.name} (Portfolio: {p.portfolio_id})")
            
        employees = Employee.query.filter_by(company_id=cid).all()
        print(f"EMPLOYEES ({len(employees)}):")
        for e in employees:
            print(f" - [{e.id}] {e.name} ({e.email})")

if __name__ == "__main__":
    inspect()
