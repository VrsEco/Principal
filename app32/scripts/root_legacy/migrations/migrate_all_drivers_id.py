from database.postgres_helper import connect

def fix_table(cursor, table_name):
    print(f"Checking table {table_name}...")
    cursor.execute(f"""
        SELECT column_name, column_default
        FROM information_schema.columns
        WHERE table_name = '{table_name}' AND column_name = 'id';
    """)
    row = cursor.fetchone()
    if row and row[1] is None:
        print(f"Table {table_name} id has NO DEFAULT. Fixing...")
        seq_name = f"{table_name}_id_seq"
        
        # Check if sequence exists
        cursor.execute(f"SELECT 1 FROM pg_class WHERE relname = '{seq_name}'")
        if not cursor.fetchone():
            cursor.execute(f"CREATE SEQUENCE {seq_name}")
            
        cursor.execute(f"ALTER TABLE {table_name} ALTER COLUMN id SET DEFAULT nextval('{seq_name}')")
        cursor.execute(f"SELECT setval('{seq_name}', COALESCE((SELECT MAX(id) FROM {table_name}), 0) + 1)")
        print(f"Table {table_name} fixed!")
    else:
        print(f"Table {table_name} is already OK or not found.")

def migrate():
    conn = connect()
    cursor = conn.cursor()
    
    try:
        tables = ['vision_records', 'market_records', 'company_records', 'interview_records', 'directional_records']
        for table in tables:
            fix_table(cursor, table)
        
        conn.commit()
        print("\nAll migrations completed!")
    except Exception as e:
        conn.rollback()
        print(f"Migration failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
