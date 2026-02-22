
import sys
import os
from sqlalchemy import text

sys.path.append(os.getcwd())
from app import create_app, db

app = create_app()

def list_tables():
    with app.app_context():
        print("--- TABLES ---")
        with db.engine.connect() as conn:
            # Query pg_catalog
            res = conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename"))
            for r in res:
                print(r[0])

if __name__ == "__main__":
    list_tables()
