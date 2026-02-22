import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import app
from models.user import User
from services.my_work_service import get_user_employees, _get_company_activities_unrestricted
from database.postgres_helper import connect as pg_connect

with app.app_context():
    print("Testando fluxo da API My Work...")
    user = User.query.filter_by(role='admin').first()
    print(f"Usuario: {user.email}, Role: {user.role}, ID: {user.id}")

    from models.company import Company
    all_companies = Company.query.all()
    accessible_company_ids = [c.id for c in all_companies]
    
    user_employees = get_user_employees(user.id)
    all_employee_ids = [e['employee_id'] for e in user_employees if e.get('employee_id')]

    print(f"Empresas Acessiveis: {len(accessible_company_ids)} ids -> {accessible_company_ids[:5]}...")
    print(f"Employee IDs do Usuario: {all_employee_ids}")

    effective_company_ids = accessible_company_ids
    filters = {
        "delivery_tags": ["open"],
        "sort": "deadline"
    }

    print("\nExecutando _get_company_activities_unrestricted...")
    conn = pg_connect()
    cursor = conn.cursor()
    try:
        activities = _get_company_activities_unrestricted(
            cursor, effective_company_ids, filters=filters
        )
        print(f"Total de Atividades Unrestricted Recuperadas: {len(activities)}")
        if activities:
            print(f" - Exemplo primeira atividade: {activities[0].get('title')} | tipo: {activities[0].get('type')} | req: {activities[0].get('owner_id')} | emp_id: {activities[0].get('company_id')}")
    except Exception as e:
        print(f"Erro ao buscar atividades: {e}")
    finally:
        conn.close()

    print("\n--- FIM ---\n")
