from database.postgres_helper import connect
import json

def check_routine_for_process():
    try:
        conn = connect()
        cursor = conn.cursor()
        
        # Get the latest instance to find its process
        cursor.execute("""
            SELECT id, instance_code, process_id, routine_id
            FROM process_instances 
            ORDER BY id DESC
            LIMIT 1
        """)
        instance = cursor.fetchone()
        
        if not instance:
            print("No instances found!")
            conn.close()
            return
        
        print(f"Latest Instance: {instance['instance_code']}")
        print(f"Process ID: {instance['process_id']}")
        print(f"Routine ID (in instance): {instance['routine_id']}")
        
        # Find routine for this process
        cursor.execute("""
            SELECT id, process_id, assigned_roles, company_id
            FROM routines
            WHERE process_id = %s
            LIMIT 1
        """, (instance['process_id'],))
        
        routine = cursor.fetchone()
        
        if not routine:
            print(f"\n❌ NO ROUTINE FOUND for process {instance['process_id']}!")
            print("This is why assigned_collaborators is empty!")
        else:
            print(f"\n{'='*80}")
            print(f"Routine Found:")
            print(f"  ID: {routine['id']}")
            print(f"  Process ID: {routine['process_id']}")
            print(f"  Company ID: {routine['company_id']}")
            print(f"\nAssigned Roles (raw):")
            print(f"  Type: {type(routine['assigned_roles'])}")
            print(f"  Value: {routine['assigned_roles']}")
            
            if routine['assigned_roles']:
                try:
                    if isinstance(routine['assigned_roles'], str):
                        parsed = json.loads(routine['assigned_roles'])
                    else:
                        parsed = routine['assigned_roles']
                    
                    print(f"\nParsed ({len(parsed)} roles):")
                    print(json.dumps(parsed, indent=2, ensure_ascii=False))
                    
                    # Check if employees exist
                    for role in parsed:
                        emp_id = role.get('employee_id')
                        if emp_id:
                            cursor.execute("SELECT id, name FROM employees WHERE id = %s", (emp_id,))
                            emp = cursor.fetchone()
                            if emp:
                                print(f"\n  ✅ Employee {emp_id}: {emp['name']}")
                            else:
                                print(f"\n  ❌ Employee {emp_id}: NOT FOUND!")
                except Exception as e:
                    print(f"\n❌ Parse error: {e}")
            else:
                print("\n⚠️  Routine has NO assigned_roles!")
        
        conn.close()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_routine_for_process()
