from database.postgres_helper import connect
import json

def check_routine_and_recent_instances():
    try:
        conn = connect()
        cursor = conn.cursor()
        
        # Get instance AL.P95.006 with creation date
        cursor.execute("""
            SELECT id, instance_code, title, assigned_collaborators, 
                   process_id, routine_id, created_at, trigger_type
            FROM process_instances 
            WHERE instance_code = 'AL.P95.006'
        """)
        row = cursor.fetchone()
        
        if row:
            print(f"=== Instance {row['instance_code']} ===")
            print(f"Created at: {row['created_at']}")
            print(f"Trigger type: {row['trigger_type']}")
            print(f"Process ID: {row['process_id']}")
            print(f"Routine ID: {row['routine_id']}")
            print(f"Assigned Collaborators: {row['assigned_collaborators']}")
            
            # Check if there's a routine for this process
            if row['process_id']:
                cursor.execute("""
                    SELECT id, assigned_roles
                    FROM routines
                    WHERE process_id = %s
                    LIMIT 1
                """, (row['process_id'],))
                routine = cursor.fetchone()
                
                if routine:
                    print(f"\n=== Associated Routine ===")
                    print(f"Routine ID: {routine['id']}")
                    print(f"Assigned Roles: {routine['assigned_roles']}")
                else:
                    print(f"\n⚠️  No routine found for process {row['process_id']}")
        
        # Check most recent instances
        print("\n\n=== Most Recent 3 Instances ===")
        cursor.execute("""
            SELECT id, instance_code, title, assigned_collaborators, created_at
            FROM process_instances 
            ORDER BY id DESC
            LIMIT 3
        """)
        
        for r in cursor.fetchall():
            collab_len = 0
            if r['assigned_collaborators']:
                try:
                    parsed = json.loads(r['assigned_collaborators']) if isinstance(r['assigned_collaborators'], str) else r['assigned_collaborators']
                    collab_len = len(parsed) if isinstance(parsed, list) else 0
                except:
                    pass
            
            print(f"\n{r['instance_code']}: {r['title']}")
            print(f"  Created: {r['created_at']}")
            print(f"  Collaborators: {collab_len} items")
            print(f"  Raw: {r['assigned_collaborators'][:100] if r['assigned_collaborators'] else 'NULL'}")
            
        conn.close()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_routine_and_recent_instances()
