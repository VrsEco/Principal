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
        print("Checking actual column nullability in occurrences:")
        res = conn.execute(text("""
            SELECT column_name, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'occurrences';
        """))
        for row in res:
            print(f"Col: {row[0]}, Nullable: {row[1]}")
            
    with engine.connect() as conn:
        with conn.begin():
            print("\nEnsuring project_id and process_id are also nullable just in case...")
            conn.execute(text("ALTER TABLE occurrences ALTER COLUMN project_id DROP NOT NULL;"))
            conn.execute(text("ALTER TABLE occurrences ALTER COLUMN process_id DROP NOT NULL;"))
            conn.execute(text("ALTER TABLE occurrences ALTER COLUMN collaborators_ids DROP NOT NULL;"))
            print("\nFix applied.")
except Exception as e:
    print(f"Error: {e}")
