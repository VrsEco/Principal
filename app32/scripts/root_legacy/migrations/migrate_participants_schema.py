"""
Migration script to make the 'name' column nullable in participants table.
This allows the new SQLAlchemy model to work with employee_id foreign key.
"""
from config_database import get_db

db = get_db()
conn = db._get_connection()
cursor = conn.cursor()

try:
    print("Making 'name' column nullable in participants table...")
    cursor.execute("""
        ALTER TABLE participants 
        ALTER COLUMN name DROP NOT NULL
    """)
    conn.commit()
    print("✓ Successfully updated participants table schema")
    print("  - name column is now nullable")
except Exception as e:
    conn.rollback()
    print(f"✗ Error: {e}")
finally:
    conn.close()
