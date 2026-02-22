"""
Script de diagnostico para a tela My Work (ASCII only).
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def pr(msg):
    print(msg, flush=True)

from app import app

with app.app_context():
    from database.postgres_helper import connect as pg_connect
    from services.my_work_service import (
        get_employee_from_user,
        get_user_employees,
        _fetch_projects_for_employee,
        _fetch_processes_for_employee,
        _fetch_normalized_process_rows,
        _project_activities_table_available,
        _process_collaborators_table_available,
    )
    from models.user import User

    pr("=" * 60)
    pr("DIAGNOSTICO MY WORK")
    pr("=" * 60)

    users = User.query.all()
    pr(f"\n[1] Total de usuarios: {len(users)}")
    for u in users[:5]:
        pr(f"   - ID: {u.id}, Email: {u.email}, Role: {u.role}")

    # Encontrar usuario com employee_id
    test_user = None
    test_emp_id = None
    for u in users:
        emp_id = get_employee_from_user(u.id)
        companies = get_user_employees(u.id)
        pr(f"   User {u.id} ({u.email}): employee_id={emp_id}, n_empresas={len(companies)}")
        if emp_id and test_emp_id is None:
            test_user = u
            test_emp_id = emp_id

    if not test_emp_id:
        pr("\nNENHUM USUARIO COM EMPLOYEE_ID VINCULADO!")
        sys.exit(1)

    pr(f"\n[TEST] User ID={test_user.id}, Employee ID={test_emp_id}")

    conn = pg_connect()
    cursor = conn.cursor()

    pr("\n[4] Verificacao de tabelas:")
    proj_table = _project_activities_table_available(cursor)
    proc_table = _process_collaborators_table_available(cursor)
    pr(f"   - project_activities existe: {proj_table}")
    pr(f"   - process_instance_collaborators existe: {proc_table}")

    pr("\n[5] Contagens diretas no banco:")
    cursor.execute("SELECT COUNT(*) FROM process_instances")
    pr(f"   - Total process_instances: {cursor.fetchone()[0]}")
    cursor.execute("SELECT COUNT(*) FROM company_projects")
    pr(f"   - Total company_projects: {cursor.fetchone()[0]}")

    try:
        cursor.execute("SELECT COUNT(*) FROM project_activities WHERE employee_id = %s", (test_emp_id,))
        pr(f"   - project_activities para emp {test_emp_id}: {cursor.fetchone()[0]}")
    except Exception as e:
        pr(f"   - project_activities: {e}")

    try:
        cursor.execute("SELECT COUNT(*) FROM process_instance_collaborators WHERE employee_id = %s", (test_emp_id,))
        pr(f"   - proc_instance_collaborators para emp {test_emp_id}: {cursor.fetchone()[0]}")
    except Exception as e:
        pr(f"   - process_instance_collaborators: {e}")

    pr("\n[6] Projetos do colaborador (legacy query):")
    try:
        leg_proj = _fetch_projects_for_employee(cursor, test_emp_id)
        pr(f"   - legacy project_rows: {len(leg_proj)} registros")
        if leg_proj:
            r = dict(leg_proj[0])
            pr(f"   - Exemplo: id={r.get('id')}, title={r.get('title')}, company_id={r.get('company_id')}")
    except Exception as e:
        pr(f"   - ERRO: {e}")
        import traceback; traceback.print_exc()

    pr("\n[7] Processos do colaborador (normalized):")
    try:
        norm_proc = _fetch_normalized_process_rows(cursor, employee_ids=[test_emp_id])
        pr(f"   - normalized process_rows: {len(norm_proc)} registros")
        if norm_proc:
            r = norm_proc[0]
            pr(f"   - Exemplo: id={r.get('id')}, title={r.get('title')}, company_id={r.get('company_id')}")
    except Exception as e:
        pr(f"   - ERRO: {e}")
        import traceback; traceback.print_exc()

    pr("\n[8] Processos do colaborador (legacy):")
    try:
        leg_proc = _fetch_processes_for_employee(cursor, test_emp_id)
        pr(f"   - legacy process_rows: {len(leg_proc)} registros")
        if leg_proc:
            r = dict(leg_proc[0])
            pr(f"   - Exemplo: id={r.get('id')}, title={r.get('title')}, company_id={r.get('company_id')}")
    except Exception as e:
        pr(f"   - ERRO: {e}")
        import traceback; traceback.print_exc()

    pr("\n[9] get_user_activities(scope='me'):")
    from services.my_work_service import get_user_activities
    try:
        acts = get_user_activities(test_emp_id, scope='me')
        pr(f"   - Retornou {len(acts)} atividades no scope=me")
        if acts:
            a = acts[0]
            pr(f"   - 1o: type={a.get('type')}, id={a.get('id')}, title={str(a.get('title'))[:40]}")
    except Exception as e:
        pr(f"   - ERRO: {e}")
        import traceback; traceback.print_exc()

    pr("\n[10] get_user_activities(scope='company'):")
    try:
        # Verificar _can_view_company
        from services.my_work_service import _can_view_company
        can_view = _can_view_company(cursor, test_emp_id)
        pr(f"   _can_view_company={can_view}")

        company_id_of_emp = None
        cursor.execute("SELECT company_id FROM employees WHERE id = %s", (test_emp_id,))
        row = cursor.fetchone()
        if row:
            company_id_of_emp = row[0]
        pr(f"   company_id do employee: {company_id_of_emp}")

        if company_id_of_emp:
            acts2 = get_user_activities(test_emp_id, scope='company', company_ids=[company_id_of_emp])
            pr(f"   - Retornou {len(acts2)} atividades no scope=company para company_id={company_id_of_emp}")
    except Exception as e:
        pr(f"   - ERRO: {e}")
        import traceback; traceback.print_exc()

    conn.close()
    pr("\n" + "=" * 60)
    pr("FIM DO DIAGNOSTICO")
    pr("=" * 60)
