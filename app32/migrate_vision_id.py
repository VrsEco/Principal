from database.postgres_helper import connect

def migrate():
    conn = connect()
    cursor = conn.cursor()
    
    try:
        # Check if sequence exists
        cursor.execute("SELECT 1 FROM pg_class WHERE relname = 'vision_records_id_seq'")
        if not cursor.fetchone():
            print("Creating sequence vision_records_id_seq...")
            cursor.execute("CREATE SEQUENCE vision_records_id_seq")
            
        # Alter column to use sequence
        print("Setting default for vision_records.id...")
        cursor.execute("ALTER TABLE vision_records ALTER COLUMN id SET DEFAULT nextval('vision_records_id_seq')")
        
        # Sync sequence
        print("Syncing sequence...")
        cursor.execute("SELECT setval('vision_records_id_seq', COALESCE((SELECT MAX(id) FROM vision_records), 0) + 1)")
        
        conn.commit()
        print("Migration successful!")
    except Exception as e:
        conn.rollback()
        print(f"Migration failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
