from app import create_app
from models import db
from sqlalchemy import text

app = create_app()
with app.app_context():
    print("Adding 'performance_ranges' column to indicator_goals...")
    try:
        # Adicionar a coluna performance_ranges (JSON) se ela não existir
        db.session.execute(text("ALTER TABLE indicator_goals ADD COLUMN IF NOT EXISTS performance_ranges JSON"))
        db.session.commit()
        print("Column 'performance_ranges' added successfully.")
    except Exception as e:
        db.session.rollback()
        print(f"Error adding column: {e}")
