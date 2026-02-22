from database.postgres_helper import connect

def check_routines_schema():
    try:
        conn = connect()
        cursor = conn.cursor()
        
        # Get table schema
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'routines'
            ORDER BY ordinal_position
        """)
        
        print("=== ROUTINES TABLE SCHEMA ===")
        for row in cursor.fetchall():
            print(f"  {row['column_name']}: {row['data_type']}")
        
        # Get a sample routine
        print("\n=== SAMPLE ROUTINE (Process 95) ===")
        cursor.execute("""
            SELECT *
            FROM routines
            WHERE process_id = 95
            LIMIT 1
        """)
        
        routine = cursor.fetchone()
        if routine:
            for key in routine.keys():
                value = routine[key]
                if value and len(str(value)) > 100:
                    print(f"  {key}: {str(value)[:100]}...")
                else:
                    print(f"  {key}: {value}")
        else:
            print("  No routine found for process 95")
        
        conn.close()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_routines_schema()
