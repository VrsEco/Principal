from app import create_app, db
from sqlalchemy import text

app = create_app()
with app.app_context():
    res = db.session.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'process_steps'")).fetchall()
    print("process_steps columns:")
    for row in res:
        print(f"Column: {row[0]}, Type: {row[1]}")
