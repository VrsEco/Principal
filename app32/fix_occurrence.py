import os
from sqlalchemy import create_engine, text
try:
    from config import Config
    db_uri = Config.SQLALCHEMY_DATABASE_URI
except:
    db_uri = "postgresql://postgres:postgres@localhost:5432/gestao_versus"

engine = create_engine(db_uri)
try:
    with engine.connect() as conn:
        with conn.begin():
            print("Checking occurrences table null capability...")
            # Drop the NOT NULL constraint on employee_id
            conn.execute(text("ALTER TABLE occurrences ALTER COLUMN employee_id DROP NOT NULL;"))
            print("Successfully made employee_id nullable in occurrences table.")
except Exception as e:
    print(f"Error: {e}")
