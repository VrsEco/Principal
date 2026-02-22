from database import get_db
db = get_db()
conn = db._get_connection()
cursor = conn.cursor()

# Check if columns exist first
cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'process_steps' AND table_schema = 'public'")
cols = {row[0] for row in cursor.fetchall()}

if 'layout' not in cols:
    print("Adding layout column...")
    cursor.execute("ALTER TABLE process_steps ADD COLUMN layout VARCHAR(50) DEFAULT 'single'")

if 'image_path' not in cols:
    print("Adding image_path column...")
    cursor.execute("ALTER TABLE process_steps ADD COLUMN image_path VARCHAR(255)")

if 'image_width' not in cols:
    print("Adding image_width column...")
    cursor.execute("ALTER TABLE process_steps ADD COLUMN image_width INTEGER DEFAULT 280")

conn.commit()
conn.close()
print("Migration completed.")
