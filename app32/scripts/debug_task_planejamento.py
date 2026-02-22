"""
Diagnóstico específico: Busca a atividade do projeto V20.J.26
e simula exatamente o que o My Work faria para o admin.
"""
from app import app

with app.app_context():
    from database.postgres_helper import connect as pg_connect
    from services.my_work_service import (
        get_employee_from_user, get_user_employees,
        _fetch_v2_project_rows, _project_activity_row_from_normalized
    )
    from models.user import User
    from models import Company

    conn = pg_connect()
    cursor = conn.cursor()

    # 1. Buscar o projeto V20.J.26 (project id=26)
    print('=== PROJETO V20.J.26 (id=26) ===')
    cursor.execute("""
        SELECT p.id, p.title, p.company_id, p.status, c.name AS company_name, c.client_code
        FROM projects p
        LEFT JOIN companies c ON c.id = p.company_id
        WHERE p.id = 26
    """)
    proj = cursor.fetchone()
    if proj:
        print(f'  ID={proj["id"]}, Titulo={proj["title"]}, company_id={proj["company_id"]}, '
              f'company={proj["company_name"]}, code={proj["client_code"]}')
    else:
        print('  Projeto id=26 NÃO encontrado')

    # 2. Buscar TODAS as tasks desse projeto
    print()
    print('=== TASKS DO PROJETO 26 ===')
    cursor.execute("""
        SELECT pt.id, pt.what, pt.employee_id, pt.status, pt.stage, pt.due_date,
               e.name AS employee_name, pt.created_at
        FROM project_tasks pt
        LEFT JOIN employees e ON e.id = pt.employee_id
        WHERE pt.project_id = 26
        ORDER BY pt.created_at DESC
    """)
    tasks = cursor.fetchall()
    if tasks:
        for t in tasks:
            d = dict(t)
            print(f'  task_id={d["id"]}, what={d["what"][:60]}, '
                  f'employee_id={d["employee_id"]}, employee={d["employee_name"]}, '
                  f'stage={d["stage"]}, created={d["created_at"]}')
    else:
        print('  Nenhuma task encontrada no projeto 26')
        
        # Tenta buscar por nome
        print()
        print('=== BUSCANDO TASK POR NOME ===')
        cursor.execute("""
            SELECT pt.id, pt.what, pt.employee_id, pt.project_id, pt.stage,
                   e.name AS employee_name, p.title AS project_title, p.company_id,
                   pt.created_at
            FROM project_tasks pt
            LEFT JOIN employees e ON e.id = pt.employee_id
            LEFT JOIN projects p ON p.id = pt.project_id
            WHERE LOWER(pt.what) LIKE '%planejamento%'
               OR LOWER(pt.what) LIKE '%crescimento%'
               OR LOWER(pt.what) LIKE '%teste%projeto%'
            ORDER BY pt.created_at DESC
            LIMIT 5
        """)
        for t in cursor.fetchall():
            d = dict(t)
            print(f'  task_id={d["id"]}, what={d["what"][:60]}, project={d["project_title"]}, '
                  f'employee={d["employee_name"]}, stage={d["stage"]}, created={d["created_at"]}')

    # 3. Simular exatamente o que _fetch_v2_project_rows faz para employee_id=71
    print()
    print('=== SIMULAÇÃO: _fetch_v2_project_rows(employee_ids=[71]) ===')
    try:
        rows = _fetch_v2_project_rows(cursor, employee_ids=[71])
        print(f'  Retornou {len(rows)} atividades')
        for r in rows[:5]:
            print(f'  → activity_id={r.get("activity_id")}, title={str(r.get("title",""))[:50]}, '
                  f'company_id={r.get("company_id")}, responsible_id={r.get("responsible_id")}')
    except Exception as e:
        print(f'  ERRO: {e}')
        import traceback
        traceback.print_exc()

    # 4. Verificar se a tabela project_activities existe
    print()
    print('=== TABELAS EXISTENTES ===')
    cursor.execute("""
        SELECT table_name FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name IN ('project_activities', 'project_tasks', 'project_activity_collaborators')
    """)
    tables = [r[0] for r in cursor.fetchall()]
    print(f'  Tabelas: {tables}')

    # 5. Verificar company_ids do admin
    print()
    print('=== ADMIN: employee_ids e company_ids ===')
    admin = User.query.filter_by(email='admin@gestaoversus.com.br').first()
    if admin:
        employee_id = get_employee_from_user(admin.id)
        user_employees = get_user_employees(admin.id)
        all_employee_ids = [e['employee_id'] for e in user_employees if e.get('employee_id')]
        all_company_ids = [e['company_id'] for e in user_employees if e.get('company_id')]
        all_companies = Company.query.all()
        accessible_company_ids = [c.id for c in all_companies]
        
        print(f'  employee_id principal: {employee_id}')
        print(f'  all_employee_ids: {all_employee_ids}')
        print(f'  company_ids via employees: {all_company_ids}')
        print(f'  ALL company_ids (admin): {accessible_company_ids}')
        print(f'  Company V20 (id=37) no accessible? {37 in accessible_company_ids}')

    conn.close()
    print()
    print('=== FIM DO DIAGNÓSTICO ===')
