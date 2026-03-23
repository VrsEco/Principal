import os
from app import create_app
from database import get_db

app = create_app()

with app.app_context():
    try:
        pg = get_db()
        conn = pg._get_connection()
        cursor = conn.cursor()
        
        # Check if column exists
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='process_instances' AND column_name='actual_end_date';
        """)
        
        if not cursor.fetchone():
            print("Adding actual_end_date column...")
            cursor.execute("ALTER TABLE process_instances ADD COLUMN actual_end_date DATE;")
            conn.commit()
            print("Column added successfully.")
        else:
            print("Column actual_end_date already exists.")
            
        conn.close()
    except Exception as e:
        print(f"Error: {e}")
