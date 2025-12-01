from database.postgres_helper import connect

def check_process_instances_schema():
    try:
        conn = connect()
        cursor = conn.cursor()
        
        # Get table schema
        cursor.execute("""
            SELECT column_name, data_type, character_maximum_length, is_nullable
            FROM information_schema.columns 
            WHERE table_name = 'process_instances'
            ORDER BY ordinal_position
        """)
        
        print("="*80)
        print("PROCESS_INSTANCES TABLE SCHEMA")
        print("="*80)
        
        for row in cursor.fetchall():
            nullable = "NULL" if row['is_nullable'] == 'YES' else "NOT NULL"
            max_len = f"({row['character_maximum_length']})" if row['character_maximum_length'] else ""
            print(f"{row['column_name']:30} {row['data_type']}{max_len:20} {nullable}")
        
        # Get a sample instance
        print("\n" + "="*80)
        print("SAMPLE INSTANCE (AL.P95.010)")
        print("="*80)
        
        cursor.execute("""
            SELECT *
            FROM process_instances
            WHERE instance_code = 'AL.P95.010'
        """)
        
        instance = cursor.fetchone()
        if instance:
            for key in sorted(instance.keys()):
                value = instance[key]
                if value and isinstance(value, str) and len(value) > 80:
                    print(f"{key:30} {str(value)[:80]}...")
                else:
                    print(f"{key:30} {value}")
        else:
            print("Instance not found")
        
        conn.close()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_process_instances_schema()
