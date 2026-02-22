"""
Diagnóstico: Por que a atividade 'V20.J.26 Teste Projeto Planejamento Crescimento'
não aparece no My Work do admin?
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app

with app.app_context():
    from models.user import User
    from models.employee import Employee
    from models.project import Project, ProjectTask
    from database.postgres_helper import connect as pg_connect
    
    # Buscar admin
    admin = User.query.filter_by(email='admin@gestaoversus.com.br').first()
    print('=== ADMIN USER ===')
    if admin:
        print(f'  ID: {admin.id}, Email: {admin.email}, Role: {admin.role}')
    else:
        print('  ADMIN NÃO ENCONTRADO')

    # Buscar employee do admin
    emp_admin = Employee.query.filter_by(user_id=admin.id).first() if admin else None
    if emp_admin:
        print(f'  Employee vinculado: ID={emp_admin.id}, Nome={emp_admin.name}')
    else:
        emp_by_email = Employee.query.filter(Employee.email.ilike(admin.email)).first() if admin else None
        if emp_by_email:
            print(f'  Employee por email: ID={emp_by_email.id}, Nome={emp_by_email.name}, user_id={emp_by_email.user_id}')
        else:
            print('  Nenhum employee vinculado ao admin')
    
    # Buscar 'Diretor Marcos'
    print()
    print('=== COLABORADORES COM "MARCOS" ===')
    marcos_list = Employee.query.filter(Employee.name.ilike('%marcos%')).all()
    for m in marcos_list:
        print(f'  ID={m.id}, Nome={m.name}, user_id={m.user_id}, email={m.email}')
    if not marcos_list:
        print('  Nenhum colaborador com "Marcos" encontrado')
    
    # Buscar a atividade criada
    print()
    print('=== ATIVIDADES RECENTES DE PROJETO ===')
    conn = pg_connect()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT pt.id, pt.what, pt.employee_id, pt.status, pt.stage, pt.due_date,
               e.name AS employee_name, p.title AS project_name, p.company_id
        FROM project_tasks pt
        JOIN projects p ON p.id = pt.project_id
        LEFT JOIN employees e ON e.id = pt.employee_id
        ORDER BY pt.created_at DESC
        LIMIT 10
    """)
    rows = cursor.fetchall()
    for r in rows:
        d = dict(r)
        print(f'  task_id={d["id"]}, what={d["what"][:50]}, employee_id={d["employee_id"]}, '
              f'employee={d["employee_name"]}, company_id={d["company_id"]}, stage={d["stage"]}')
    
    print()
    print('=== DIAGNÓSTICO _fetch_v2_project_rows ===')
    if admin:
        from services.my_work_service import get_employee_from_user, get_user_employees
        employee_id = get_employee_from_user(admin.id)
        print(f'  get_employee_from_user({admin.id}) = {employee_id}')
        
        user_employees = get_user_employees(admin.id)
        print(f'  get_user_employees = {user_employees}')
        
        all_employee_ids = [e['employee_id'] for e in user_employees if e.get('employee_id')]
        print(f'  all_employee_ids = {all_employee_ids}')
    
    conn.close()
    print()
    print('=== CONCLUSÃO ===')
    print('Se employee_id do admin != employee_id do Diretor Marcos,')
    print('a atividade não aparecerá no My Work com scope="me".')
