from database.postgres_helper import connect

conn = connect()
cursor = conn.cursor()
cursor.execute("""
    SELECT column_name, data_type, column_default, is_nullable
    FROM information_schema.columns
    WHERE table_name = 'vision_records' AND column_name = 'id';
""")
row = cursor.fetchone()
if row:
    print(f"ID Column Info: {list(row)}")
else:
    print("ID column not found!")
conn.close()
