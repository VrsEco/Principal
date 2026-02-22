from src.core.database import db
from app import create_app
from sqlalchemy import text

app = create_app()
with app.app_context():
    with db.engine.connect() as conn:
        result = conn.execute(text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'companies'
        """))
        print("Columns in 'companies' table:")
        for row in result:
            print(f"- {row[0]}: {row[1]}")
