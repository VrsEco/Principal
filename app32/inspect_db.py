from app import create_app
from models import db
from sqlalchemy import text

app = create_app()
with app.app_context():
    with db.engine.connect() as conn:
        # Check foreign keys on incentive_rules
        query = text("""
            SELECT
                tc.table_name, kcu.column_name, 
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name 
            FROM 
                information_schema.table_constraints AS tc 
                JOIN information_schema.key_column_usage AS kcu
                  ON tc.constraint_name = kcu.constraint_name
                JOIN information_schema.constraint_column_usage AS ccu
                  ON ccu.constraint_name = tc.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_name='incentive_rules';
        """)
        result = conn.execute(query)
        print("FOREIGN KEYS ON incentive_rules:")
        for row in result:
            print(f"{row.column_name} -> {row.foreign_table_name}.{row.foreign_column_name}")
        
        # Also check all tables
        result = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public'"))
        print("\nALL TABLES:")
        tables = [r[0] for r in result]
        print(", ".join(tables))
