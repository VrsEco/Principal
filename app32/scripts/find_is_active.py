from app import create_app, db
from sqlalchemy import text

app = create_app()
with app.app_context():
    res = db.session.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'routines'")).fetchall()
    print("Routines columns:")
    for row in res:
        if 'active' in row[0].lower():
            print(f"MATCH: Column: {row[0]}, Type: {row[1]}")
