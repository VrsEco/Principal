from database.postgres_helper import connect
import json

def check_latest_instances():
    try:
        conn = connect()
        cursor = conn.cursor()
        
        # Get the 3 most recent instances
        cursor.execute("""
            SELECT id, instance_code, title, assigned_collaborators, 
                   process_id, routine_id, created_at, trigger_type
            FROM process_instances 
            ORDER BY id DESC
            LIMIT 3
        """)
        
        instances = cursor.fetchall()
        
        if not instances:
            print("No instances found!")
            conn.close()
            return
        
        for row in instances:
            print(f"\n{'='*80}")
            print(f"Instance: {row['instance_code']} - {row['title']}")
            print(f"ID: {row['id']}")
            print(f"Created: {row['created_at']}")
            print(f"Trigger: {row['trigger_type']}")
            print(f"Process ID: {row['process_id']}")
            print(f"Routine ID: {row['routine_id']}")
            print(f"\nAssigned Collaborators (raw):")
            print(f"  Type: {type(row['assigned_collaborators'])}")
            print(f"  Value: {row['assigned_collaborators']}")
            
            # Parse and display
            if row['assigned_collaborators']:
                try:
                    if isinstance(row['assigned_collaborators'], str):
                        parsed = json.loads(row['assigned_collaborators'])
                    else:
                        parsed = row['assigned_collaborators']
                    
                    print(f"\nParsed ({len(parsed)} collaborators):")
                    if parsed:
                        print(json.dumps(parsed, indent=2, ensure_ascii=False))
                        
                        # Categorize by role
                        owners = [c for c in parsed if c.get('role') == 'owner']
                        responsibles = [c for c in parsed if c.get('role') == 'responsible']
                        executors = [c for c in parsed if c.get('role') == 'executor']
                        
                        print(f"\nBy Role:")
                        print(f"  Owners: {[c.get('name') for c in owners]}")
                        print(f"  Responsibles: {[c.get('name') for c in responsibles]}")
                        print(f"  Executors: {[c.get('name') for c in executors]}")
                    else:
                        print("  ⚠️  Empty array!")
                except Exception as e:
                    print(f"\n  ❌ Parse error: {e}")
            else:
                print("  ⚠️  NULL or empty!")
        
        conn.close()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_latest_instances()
