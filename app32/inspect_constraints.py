from app import create_app
from models import db
from sqlalchemy import text

app = create_app()
with app.app_context():
    print("Inspecting constraints for indicator_goals...")
    query = text("""
        SELECT
            conname AS constraint_name,
            pg_get_constraintdef(c.oid) AS constraint_definition
        FROM
            pg_constraint c
        JOIN
            pg_namespace n ON n.oid = c.connamespace
        WHERE
            conrelid = 'indicator_goals'::regclass;
    """)
    result = db.session.execute(query).fetchall()
    for row in result:
        print(f"Constraint: {row.constraint_name}")
        print(f"Definition: {row.constraint_definition}")
