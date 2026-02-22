from app import create_app, db
from sqlalchemy import text

app = create_app()
with app.app_context():
    sql = """
    SELECT conname, pg_get_constraintdef(c.oid)
    FROM pg_constraint c
    JOIN pg_namespace n ON n.oid = c.connamespace
    WHERE n.nspname = 'public' AND conrelid = 'process_steps'::regclass;
    """
    res = db.session.execute(text(sql)).fetchall()
    print("START_CONSTRAINTS")
    for row in res:
        print(f"NAME: {row[0]}")
        print(f"DEF: {row[1]}")
    print("END_CONSTRAINTS")
