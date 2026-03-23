from config_database import get_db

db = get_db()
conn = db._get_connection()
cursor = conn.cursor()

# Check if section_status table exists
cursor.execute("""
    SELECT EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name = 'section_status'
    )
""")
exists = cursor.fetchone()[0]

print(f"Table 'section_status' exists: {exists}")

if exists:
    # Check schema
    cursor.execute("""
        SELECT column_name, data_type, is_nullable 
        FROM information_schema.columns 
        WHERE table_name = 'section_status' 
        ORDER BY ordinal_position
    """)
    
    print("\nTable schema:")
    print("-" * 60)
    for row in cursor.fetchall():
        print(f"{row['column_name']:20} {row['data_type']:20} nullable={row['is_nullable']}")
    
    # Check if there are any records for plan 43
    cursor.execute("SELECT * FROM section_status WHERE plan_id = 43")
    records = cursor.fetchall()
    print(f"\nRecords for plan_id=43: {len(records)}")
    for rec in records:
        print(f"  - {rec['section_name']}: {rec['status']}")
else:
    print("\n❌ Table does not exist! Need to create it.")

conn.close()
