
import sys
import os
from sqlalchemy import text

sys.path.append(os.getcwd())
try:
    from app import create_app, db
except ImportError:
    pass

def inspect_fks(table_name):
    app = create_app()
    with app.app_context():
        print(f"--- INSPECTING FOREIGN KEYS TO {table_name} ---")
        sql = """
        SELECT
            tc.table_name, 
            kcu.column_name
        FROM 
            information_schema.table_constraints AS tc 
            JOIN information_schema.key_column_usage AS kcu
              ON tc.constraint_name = kcu.constraint_name
              AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage AS ccu
              ON ccu.constraint_name = tc.constraint_name
              AND ccu.table_schema = tc.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY' AND ccu.table_name = :tn;
        """
        
        with db.engine.connect() as conn:
            result = conn.execute(text(sql), {'tn': table_name})
            rows = result.fetchall()
            if not rows:
                print("No incoming foreign keys found.")
            else:
                for r in rows:
                    print(f"Table '{r[0]}' Column '{r[1]}' references {table_name}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        inspect_fks(sys.argv[1])
    else:
        print("Usage: python inspect_fks.py <table_name>")
