from app import create_app
from models import db
from sqlalchemy import text

app = create_app()
with app.app_context():
    with db.engine.connect() as conn:
        with open('inspect_output.txt', 'w') as f:
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
            f.write("FOREIGN KEYS ON incentive_rules:\n")
            for row in result:
                f.write(f"{row.column_name} -> {row.foreign_table_name}.{row.foreign_column_name}\n")
            
            # Also check all tables
            result = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public'"))
            f.write("\nALL TABLES:\n")
            tables = [r[0] for r in result]
            f.write(", ".join(tables) + "\n")
            
            # Specifically check if indicators table has id 11
            result = conn.execute(text("SELECT id FROM indicators WHERE id=11"))
            f.write(f"\nIndicators ID 11 exists in 'indicators'? {result.fetchone() is not None}\n")
            
            # Check if there is a table called incentive_indicators
            result = conn.execute(text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'incentive_indicators')"))
            f.write(f"Does 'incentive_indicators' table exist? {result.scalar()}\n")
