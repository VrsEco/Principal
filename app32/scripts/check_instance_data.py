from database.postgres_helper import connect
import json

def check_instance_data():
    try:
        conn = connect()
        cursor = conn.cursor()
        
        # Get the most recent instance
        cursor.execute("""
            SELECT id, instance_code, title, assigned_collaborators, 
                   executor_id, responsible_id, owner_employee_id
            FROM process_instances 
            ORDER BY id DESC 
            LIMIT 5
        """)
        rows = cursor.fetchall()
        
        print(f"Found {len(rows)} recent instances:\n")
        for r in rows:
            print(f"ID: {r['id']}")
            print(f"Code: {r['instance_code']}")
            print(f"Title: {r['title']}")
            print(f"Executor ID: {r['executor_id']}")
            print(f"Responsible ID: {r['responsible_id']}")
            print(f"Owner Employee ID: {r['owner_employee_id']}")
            print(f"Assigned Collaborators JSON: {r['assigned_collaborators']}")
            
            # Parse JSON
            if r['assigned_collaborators']:
                try:
                    collab_data = json.loads(r['assigned_collaborators']) if isinstance(r['assigned_collaborators'], str) else r['assigned_collaborators']
                    print(f"Parsed Collaborators: {json.dumps(collab_data, indent=2)}")
                except:
                    print("Failed to parse JSON")
            print("-" * 80)
            
        conn.close()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_instance_data()
