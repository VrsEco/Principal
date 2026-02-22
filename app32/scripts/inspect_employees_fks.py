
import sys
import os
from sqlalchemy import text

sys.path.append(os.getcwd())
from app import create_app, db

app = create_app()

def inspect():
    with app.app_context():
        with open('employees_fks_report.txt', 'w') as f:
            f.write("--- FOREIGN KEYS TO employees ---\n")
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
            WHERE tc.constraint_type = 'FOREIGN KEY' AND ccu.table_name = 'employees';
            """
            
            with db.engine.connect() as conn:
                result = conn.execute(text(sql))
                rows = result.fetchall()
                for r in rows:
                    f.write(f"Table '{r[0]}' Column '{r[1]}'\n")

if __name__ == "__main__":
    inspect()
