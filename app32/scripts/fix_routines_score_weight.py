import os
import sys

# Add src to path if needed
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from database import get_db

def fix_routines():
    app = create_app()
    with app.app_context():
        db_helper = get_db()
        # Use the underlying connection to run raw SQL
        conn = db_helper._get_connection()
        cursor = conn.cursor()
        try:
            print("Checking routines table for score_weight column...")
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'routines' AND column_name = 'score_weight'
            """)
            result = cursor.fetchone()
            
            if not result:
                print("Column 'score_weight' not found in 'routines' table. Adding it...")
                cursor.execute("ALTER TABLE routines ADD COLUMN score_weight NUMERIC(10, 2) DEFAULT 1.0;")
                conn.commit()
                print("Column 'score_weight' added successfully.")
            else:
                print("Column 'score_weight' already exists in 'routines' table.")
                
        except Exception as e:
            print(f"Error: {e}")
            conn.rollback()
        finally:
            conn.close()

if __name__ == "__main__":
    fix_routines()
