import sys
import os

sys.path.append(r"c:\GestaoVersus\app32")

from app import create_app
from services.my_work_service import get_user_activities, get_filter_options

app = create_app()

with app.app_context():
    from models.user import User
    from services.my_work_service import get_employee_from_user, get_user_employees
    user = User.query.filter_by(email='admin@versus.com').first()
    if not user:
        user = User.query.first()
    print(f"User: {user.email}, Role: {user.role}, ID: {user.id}")
    
    employee_id = get_employee_from_user(user.id)
    print(f"Employee ID: {employee_id}")
    
    user_employees = get_user_employees(user.id)
    print(f"User Employees: {user_employees}")
    all_employee_ids = [e['employee_id'] for e in user_employees if e.get('employee_id')]
    
    activities = get_user_activities(
        employee_id=employee_id,
        scope='company' if user.role in ['admin', 'client'] else 'me',
        filters={},
        employee_ids=all_employee_ids
    )
    print(f"Total Activities via get_user_activities: {len(activities)}")

    # Admin modo irrestrito
    if not employee_id and user.role in ('admin', 'client'):
        from services.my_work_service import _get_company_activities_unrestricted
        from database.postgres_helper import connect as pg_connect
        conn = pg_connect()
        try:
            cursor = conn.cursor()
            acts = _get_company_activities_unrestricted(cursor, [1,2,3,4,5,37,36]) 
            print(f"Total Unrestricted: {len(acts)}")
        finally:
            conn.close()
