from database.postgres_helper import connect
import json

def check_specific_instance():
    try:
        conn = connect()
        cursor = conn.cursor()
        
        # Get instance AL.P95.006
        cursor.execute("""
            SELECT id, instance_code, title, assigned_collaborators, 
                   executor_id, responsible_id, owner_employee_id,
                   process_id, routine_id
            FROM process_instances 
            WHERE instance_code = 'AL.P95.006'
        """)
        row = cursor.fetchone()
        
        if not row:
            print("Instance AL.P95.006 not found!")
            conn.close()
            return
        
        print(f"=== Instance {row['instance_code']} ===")
        print(f"ID: {row['id']}")
        print(f"Title: {row['title']}")
        print(f"Process ID: {row['process_id']}")
        print(f"Routine ID: {row['routine_id']}")
        print(f"Executor ID: {row['executor_id']}")
        print(f"Responsible ID: {row['responsible_id']}")
        print(f"Owner Employee ID: {row['owner_employee_id']}")
        print(f"\nAssigned Collaborators (raw): {row['assigned_collaborators']}")
        print(f"Type: {type(row['assigned_collaborators'])}")
        
        # Try to parse JSON
        if row['assigned_collaborators']:
            try:
                if isinstance(row['assigned_collaborators'], str):
                    collab_data = json.loads(row['assigned_collaborators'])
                else:
                    collab_data = row['assigned_collaborators']
                    
                print(f"\nParsed Collaborators ({len(collab_data)} items):")
                print(json.dumps(collab_data, indent=2, ensure_ascii=False))
                
                # Extract by role
                for collab in collab_data:
                    if isinstance(collab, dict):
                        print(f"\n  - Name: {collab.get('name')}")
                        print(f"    Role: {collab.get('role')}")
                        print(f"    Hours: {collab.get('hours')}")
            except Exception as e:
                print(f"\nFailed to parse JSON: {e}")
        else:
            print("\n⚠️  assigned_collaborators is empty or NULL!")
            
        conn.close()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_specific_instance()
