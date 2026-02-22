import sys, traceback
sys.path.insert(0, '.')
from app import app
with app.app_context():
    from database.postgres_helper import connect as pg_connect
    from services.my_work_service import _fetch_company_projects, _fetch_company_processes

    conn = pg_connect()
    c = conn.cursor()
    try:
        print("Testando _fetch_company_projects para company_id=1...")
        rows = _fetch_company_projects(c, 1)
        print(f"  projetos company 1: {len(rows)}")
        if rows:
            print(f"  primeiro: {dict(rows[0]) if hasattr(rows[0], 'keys') else rows[0]}")
    except Exception as e:
        print(f"  ERRO projetos: {e}")
        traceback.print_exc()
        c.execute("ROLLBACK")

    try:
        print("Testando _fetch_company_processes para company_id=1...")
        rows2 = _fetch_company_processes(c, 1)
        print(f"  processos company 1: {len(rows2)}")
        if rows2:
            first = dict(rows2[0]) if hasattr(rows2[0], 'keys') else rows2[0]
            print(f"  primeiro: {str(first)[:200]}")
    except Exception as e:
        print(f"  ERRO processos: {e}")
        traceback.print_exc()
        c.execute("ROLLBACK")

    conn.close()
    print("FIM")
