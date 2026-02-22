from app import app
from models import db, Plan, PlanSectionStatus

def check_statuses(plan_id):
    with app.app_context():
        plan = Plan.query.get(plan_id)
        if not plan:
            print(f"Plan {plan_id} not found.")
            return
        
        print(f"Plan: {plan.title} (ID: {plan.id}, Mode: {plan.mode})")
        
        statuses = PlanSectionStatus.query.filter_by(plan_id=plan_id).all()
        print(f"--- Section Statuses ---")
        for s in statuses:
            print(f"Key: {s.section_key}, Status: {s.status}")

if __name__ == "__main__":
    check_statuses(10)
