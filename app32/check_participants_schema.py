from config_database import get_db

db = get_db()
conn = db._get_connection()
cursor = conn.cursor()

cursor.execute("""
    SELECT column_name, data_type, is_nullable 
    FROM information_schema.columns 
    WHERE table_name = 'participants' 
    ORDER BY ordinal_position
""")

with open('participants_schema.txt', 'w') as f:
    f.write("Participants table schema:\n")
    f.write("-" * 60 + "\n")
    for row in cursor.fetchall():
        line = f"{row['column_name']:20} {row['data_type']:15} nullable={row['is_nullable']}\n"
        f.write(line)
        print(line.strip())

conn.close()
print("\nSchema saved to participants_schema.txt")
