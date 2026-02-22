from database import get_db
from app import create_app

app = create_app()
with app.app_context():
    db_helper = get_db()
    conn = db_helper._get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE public.process_instances ADD COLUMN IF NOT EXISTS score_weight numeric(10, 2) DEFAULT 1.0;")
        conn.commit()
        print("Column score_weight added successfully or already exists.")
    except Exception as e:
        print(f"Error adding column: {e}")
        conn.rollback()
    conn.close()
