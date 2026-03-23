
import os, sys
sys.path.append(os.getcwd())
from app import create_app
from models.company import Company
from models.employee import Employee

def check():
    app = create_app()
    with app.app_context():
        # Get Gandu Investimentos details
        c = Company.query.filter(Company.name.ilike('%Gandu%')).first()
        if c:
            print(f"Company: {c.name} (ID: {c.id})")
            emps = Employee.query.filter_by(company_id=c.id).all()
            for e in emps:
                print(f" - Employee: {e.name} (ID: {e.id}, UserID: {e.user_id})")
        else:
            print("Gandu Investimentos not found.")

if __name__ == "__main__":
    check()
