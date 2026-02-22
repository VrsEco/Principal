from app import create_app, db
from sqlalchemy import text

app = create_app()
with app.app_context():
    try:
        # The constraint name found was process_steps_routine_id_fkey
        print("Dropping constraint process_steps_routine_id_fkey...")
        db.session.execute(text("ALTER TABLE process_steps DROP CONSTRAINT IF EXISTS process_steps_routine_id_fkey"))
        db.session.commit()
        print("Constraint dropped successfully.")
    except Exception as e:
        print(f"Error: {e}")
        db.session.rollback()
