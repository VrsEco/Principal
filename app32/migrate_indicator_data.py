from app import create_app
from models import db
from sqlalchemy import text

app = create_app()

with app.app_context():
    print("Applying column migration for IndicatorData...")
    try:
        db.session.execute(text("ALTER TABLE indicator_data ADD COLUMN IF NOT EXISTS status VARCHAR(30) DEFAULT 'draft'"))
        db.session.execute(text("ALTER TABLE indicator_data ADD COLUMN IF NOT EXISTS is_manual BOOLEAN DEFAULT FALSE"))
        db.session.commit()
        print("Migration complete!")
    except Exception as e:
        db.session.rollback()
        print(f"Migration failed: {e}")
