from app import create_app, db
from sqlalchemy import text

app = create_app()
with app.app_context():
    res = db.session.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name IN ('routines', 'process_routines') AND column_name = 'is_active'")).fetchall()
    for row in res:
        print(f"Table: ?, Column: {row[0]}, Type: {row[1]}") # Can't get table name easily from this query without adding it to SELECT
    
    # Better query
    res = db.session.execute(text("SELECT table_name, column_name, data_type FROM information_schema.columns WHERE table_name IN ('routines', 'process_routines') AND column_name = 'is_active'")).fetchall()
    for row in res:
        print(f"Table: {row[0]}, Column: {row[1]}, Type: {row[2]}")
