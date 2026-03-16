from app import create_app
from models import db
from sqlalchemy import text

app = create_app()
with app.app_context():
    print("Migrating indicator_goals to allow NULL goal_date...")
    try:
        db.session.execute(text("ALTER TABLE indicator_goals ALTER COLUMN goal_date DROP NOT NULL"))
        db.session.commit()
        print("Migration successful: goal_date is now optional.")
    except Exception as e:
        db.session.rollback()
        print(f"Migration failed: {e}")
