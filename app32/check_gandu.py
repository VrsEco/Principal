
from app import create_app
app = create_app()
from models.user import User
from models.employee import Employee
from models.company import Company
from services.my_work_service import get_user_activities
import json

with app.app_context():
    # Buscar empresas com nome similar a Gandu
    company = Company.query.filter(Company.name.ilike('%Gandu%')).first()
    if company:
        print(f"Empresa: ID={company.id}, Name={company.name}")
        # Buscar funcionários nessa empresa
        employees = Employee.query.filter_by(company_id=company.id).all()
        for emp in employees:
            user = User.query.get(emp.user_id) if emp.user_id else None
            print(f"  Employee: ID={emp.id}, Name={emp.name}, UserID={emp.user_id}, UserName={user.name if user else 'N/A'}")
            
            # Testar get_user_activities
            print(f"  Testing get_user_activities for Employee ID={emp.id}...")
            try:
                result = get_user_activities(emp.id)
                print(f"    Type: {type(result)}")
                print(f"    Content: {str(result)[:500]}")
            except Exception as test_err:
                print(f"    ERROR in get_user_activities: {test_err}")
    else:
        print("Empresa 'Gandu' não encontrada.")
