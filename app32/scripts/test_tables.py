import sys; sys.path.insert(0, '.')
from app import app
with app.app_context():
    from database.postgres_helper import connect as pg_connect
    conn = pg_connect()
    c = conn.cursor()
    
    # Verificar tabelas existentes no schema
    c.execute("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_name IN (
            'process_instance_collaborators',
            'project_activities',
            'process_instances',
            'company_projects'
        )
        ORDER BY table_name
    """)
    tables = [r[0] for r in c.fetchall()]
    print('Tabelas existentes:', tables)
    
    # Contar registros
    for table in tables:
        c.execute(f'SELECT COUNT(*) FROM {table}')
        print(f'  {table}: {c.fetchone()[0]} registros')
    
    conn.close()
    print('OK')
