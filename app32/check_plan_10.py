from app import app
from models import db, Plan, PlanImplantationData

def check_plan_data(plan_id):
    with app.app_context():
        plan = Plan.query.get(plan_id)
        if not plan:
            print(f"Plan {plan_id} not found.")
            return
        
        print(f"Plan: {plan.title} (ID: {plan.id}, Mode: {plan.mode})")
        
        data = PlanImplantationData.query.filter_by(plan_id=plan_id).all()
        if not data:
            print("No implantation data found for this plan.")
        else:
            for item in data:
                print(f"Section: {item.section_key}")
                print(f"Content: {item.content}")
                print("-" * 20)

if __name__ == "__main__":
    check_plan_data(10)
