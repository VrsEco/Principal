from app import app
from models import Plan, Company

def check_plans():
    with app.app_context():
        plans = Plan.query.all()
        print(f"Total plans: {len(plans)}")
        for plan in plans:
            company_name = plan.company.name if plan.company else "No Company"
            print(f"ID: {plan.id}, Name: {plan.name}, Company: {company_name}")

if __name__ == "__main__":
    check_plans()
