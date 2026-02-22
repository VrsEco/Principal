
import sys
import os
from sqlalchemy import text

sys.path.append(os.getcwd())
from app import create_app, db

app = create_app()

def find_children(table_name):
    with app.app_context():
        sql = """
        SELECT
            tc.table_name
        FROM 
            information_schema.table_constraints AS tc 
            JOIN information_schema.key_column_usage AS kcu
              ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage AS ccu
              ON ccu.constraint_name = tc.constraint_name
        WHERE tc.constraint_type = 'FOREIGN KEY' AND ccu.table_name = :tn;
        """
        with db.engine.connect() as conn:
            res = conn.execute(text(sql), {'tn': table_name})
            return [r[0] for r in res.fetchall()]

def main():
    targets = ['plans', 'projects', 'routines', 'processes', 'portfolios', 'companies'] # Companies last resort
    
    deps = {}
    for t in targets:
        children = find_children(t)
        deps[t] = children
        print(f"Children of {t}: {children}")

if __name__ == "__main__":
    main()
