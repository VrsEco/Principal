import os
import sys

# Add app directories to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from models import db
from sqlalchemy import text

def add_column():
    with app.app_context():
        try:
            # Check if column exists
            result = db.session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='roles' AND column_name='permissions';
            """)).fetchone()

            if not result:
                print("Adding 'permissions' column to 'roles' table...")
                db.session.execute(text("ALTER TABLE roles ADD COLUMN permissions JSON;"))
                db.session.commit()
                print("Column added successfully.")
            else:
                print("Column 'permissions' already exists in 'roles' table.")

        except Exception as e:
            db.session.rollback()
            print(f"Error adding column: {e}")

if __name__ == '__main__':
    add_column()
