from app import create_app
from models import db
from sqlalchemy import text

app = create_app()
with app.app_context():
    with db.engine.connect() as conn:
        print("Starting DB Schema Alignment...")
        
        # 1. Identify the name of the incorrect foreign key constraint
        # We know it points to incentive_indicators.id
        find_constraint_query = text("""
            SELECT constraint_name
            FROM information_schema.key_column_usage
            WHERE table_name = 'incentive_rules' 
              AND column_name = 'indicator_id'
              AND ordinal_position = 1;
        """)
        result = conn.execute(find_constraint_query)
        constraints = [row[0] for row in result]
        
        for constraint_name in constraints:
            print(f"Dropping constraint: {constraint_name}")
            try:
                conn.execute(text(f"ALTER TABLE incentive_rules DROP CONSTRAINT \"{constraint_name}\""))
            except Exception as e:
                print(f"Error dropping {constraint_name}: {e}")

        # 2. Add the correct foreign key pointing to indicators(id)
        print("Adding correct foreign key to indicators(id)...")
        try:
            conn.execute(text("ALTER TABLE incentive_rules ADD CONSTRAINT fk_incentive_rules_indicators FOREIGN KEY (indicator_id) REFERENCES indicators(id)"))
            conn.commit()
            print("✅ Foreign key corrected to point to 'indicators' table.")
        except Exception as e:
            conn.rollback()
            print(f"❌ Error adding correct foreign key: {e}")

        # 3. Also check if there are other mismatched FKs
        # For example, rule_set_id?
        # In inspect_output it was rule_set_id -> incentive_rule_sets.id (Correct)
        # company_id -> companies.id (Correct)
        
    print("Alignment task finished.")
