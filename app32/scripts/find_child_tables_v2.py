
import sys
import os
from sqlalchemy import text

sys.path.append(os.getcwd())
try:
    from app import create_app, db
except ImportError:
    pass

def find_children(table_name):
    app = create_app()
    with app.app_context():
        sql = """
        SELECT
            tc.table_name
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
        try:
            with db.engine.connect() as conn:
                res = conn.execute(text(sql), {'tn': table_name})
                rows = [r[0] for r in res.fetchall()]
                print(f"Children of {table_name}: {rows}")
        except Exception as e:
            print(f"Error querying {table_name}: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        target = sys.argv[1]
    else:
        target = 'plans'
    find_children(target)
