from app import create_app
from database import get_db

app = create_app('default')
with app.app_context():
    db_helper = get_db()
    conn = db_helper._get_connection()
    cursor = conn.cursor()
    
    try:
        print("Adding is_active to processes...")
        cursor.execute("ALTER TABLE processes ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE")
        conn.commit()
        print("Success.")
    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()

    try:
        print("Adding is_active to process_routines...")
        cursor.execute("ALTER TABLE process_routines ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE")
        conn.commit()
        print("Success.")
    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    
    conn.close()
