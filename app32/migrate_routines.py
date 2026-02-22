from database.postgres_helper import connect as pg_connect

def add_score_weight():
    conn = pg_connect()
    cursor = conn.cursor()
    
    # Check if table exists
    cursor.execute("SELECT 1 FROM information_schema.tables WHERE table_name = 'routines'")
    if not cursor.fetchone():
        print("Table 'routines' does not exist.")
        return

    # Check if column exists
    cursor.execute("""
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'routines' AND column_name = 'score_weight'
    """)
    if not cursor.fetchone():
        print("Adding 'score_weight' column to 'routines' table...")
        cursor.execute("ALTER TABLE routines ADD COLUMN score_weight NUMERIC(5,2) DEFAULT 1.0")
        conn.commit()
    else:
        print("'score_weight' column already exists.")

    # Check for other routinely used columns in app31
    columns_to_add = [
        ('schedule_type', 'VARCHAR(50)'),
        ('schedule_value', 'TEXT'),
        ('deadline_days', 'INTEGER'),
        ('deadline_hours', 'INTEGER'),
        ('is_active', 'INTEGER DEFAULT 1')
    ]
    
    for col_name, col_type in columns_to_add:
        cursor.execute(f"""
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'routines' AND column_name = '{col_name}'
        """)
        if not cursor.fetchone():
            print(f"Adding '{col_name}' column to 'routines' table...")
            cursor.execute(f"ALTER TABLE routines ADD COLUMN {col_name} {col_type}")
            conn.commit()

    conn.close()

if __name__ == "__main__":
    add_score_weight()
