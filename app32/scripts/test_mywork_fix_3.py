import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import app
from models.user import User
from services.my_work_service import get_user_employees, _get_company_activities_unrestricted
from database.postgres_helper import connect as pg_connect
from models.company import Company

with app.app_context():
    print('Comecando Teste 3')
    user = User.query.filter_by(role='admin').first()
    print(f'Admin User: {user.email}')
    
    all_companies = Company.query.all()
    accessible_company_ids = [c.id for c in all_companies]
    print(f'Qtd Empresas: {len(accessible_company_ids)}')
    
    conn = pg_connect()
    c = conn.cursor()
    try:
        acts = _get_company_activities_unrestricted(c, accessible_company_ids, {'delivery_tags': ['open'], 'sort': 'deadline'})
        print(f'Qtd Acts Unrestricted: {len(acts)}')
        if acts:
            print(f'Exemplo Atividade: {acts[0].get("title")}')
    except Exception as e:
        print(f'Error: {e}')
    finally:
        conn.close()
