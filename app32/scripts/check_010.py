from database.postgres_helper import connect
import json

def check_instance_010():
    try:
        conn = connect()
        cursor = conn.cursor()
        
        # Get instance AL.P95.010
        cursor.execute("""
            SELECT id, instance_code, title, assigned_collaborators, 
                   process_id, routine_id, created_at
            FROM process_instances 
            WHERE instance_code = 'AL.P95.010'
        """)
        row = cursor.fetchone()
        
        if not row:
            print("Instance AL.P95.010 not found!")
            conn.close()
            return
        
        print(f"=== Instance {row['instance_code']} ===")
        print(f"ID: {row['id']}")
        print(f"Title: {row['title']}")
        print(f"Created: {row['created_at']}")
        print(f"Process ID: {row['process_id']}")
        print(f"Routine ID: {row['routine_id']}")
        print(f"\nAssigned Collaborators:")
        print(f"  Type: {type(row['assigned_collaborators'])}")
        print(f"  Raw: {row['assigned_collaborators']}")
        
        if row['assigned_collaborators']:
            try:
                if isinstance(row['assigned_collaborators'], str):
                    parsed = json.loads(row['assigned_collaborators'])
                else:
                    parsed = row['assigned_collaborators']
                
                print(f"\nParsed ({len(parsed)} items):")
                if parsed:
                    print(json.dumps(parsed, indent=2, ensure_ascii=False))
                else:
                    print("  Empty array!")
            except Exception as e:
                print(f"  Parse error: {e}")
        
        conn.close()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_instance_010()
