from database import get_db
from app import create_app

app = create_app()
with app.app_context():
    db_helper = get_db()
    conn = db_helper._get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE public.routines ADD COLUMN IF NOT EXISTS code varchar(50);")
        conn.commit()
        print("Column code added successfully to routines table or already exists.")
    except Exception as e:
        print(f"Error adding column: {e}")
        conn.rollback()
    conn.close()
