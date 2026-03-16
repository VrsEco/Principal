from app import create_app
from models import db
from sqlalchemy import text

app = create_app()
with app.app_context():
    print("Adding 'code' column to indicator_goals...")
    try:
        # Adicionar a coluna code se ela não existir
        db.session.execute(text("ALTER TABLE indicator_goals ADD COLUMN IF NOT EXISTS code VARCHAR(50)"))
        db.session.commit()
        print("Column 'code' added successfully.")
    except Exception as e:
        db.session.rollback()
        print(f"Error adding column: {e}")
