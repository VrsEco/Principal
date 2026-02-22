from app import create_app, db
from sqlalchemy import text

app = create_app()
with app.app_context():
    # Check constraints on process_steps
    sql = """
    SELECT conname, pg_get_constraintdef(c.oid)
    FROM pg_constraint c
    JOIN pg_namespace n ON n.oid = c.connamespace
    WHERE n.nspname = 'public' AND conrelid = 'process_steps'::regclass;
    """
    res = db.session.execute(text(sql)).fetchall()
    print("Constraints on process_steps:")
    for row in res:
        print(f"Constraint: {row[0]}, Definition: {row[1]}")
