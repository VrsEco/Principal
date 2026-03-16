from app import create_app
from models import db
from sqlalchemy import text

app = create_app()
with app.app_context():
    print("--- Adding source_scope and source_config ---")
    try:
        db.session.execute(text("ALTER TABLE indicators ADD COLUMN source_scope VARCHAR(50) DEFAULT 'company'"))
        db.session.execute(text("ALTER TABLE indicators ADD COLUMN source_config JSON"))
        db.session.commit()
        print("Success.")
    except Exception as e:
        db.session.rollback()
        print(f"Error: {e}")
