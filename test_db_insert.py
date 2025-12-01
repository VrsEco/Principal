from database.postgres_helper import connect
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_insert():
    try:
        conn = connect()
        cursor = conn.cursor()
        
        print("Inserting test record...")
        cursor.execute(
            """
            INSERT INTO process_instances (
                company_id, process_id, routine_id, instance_code,
                title, description, status, priority, due_date,
                assigned_collaborators, estimated_hours, trigger_type,
                created_at
            ) VALUES (
                13, 64, NULL, 'TEST-FULL-INSERT',
                'Test Full Insert', 'Desc', 'pending', 'normal', NULL,
                '[]', 0, 'manual', NOW()
            )
            RETURNING id
            """
        )
        instance_id = cursor.fetchone()[0]
        print(f"Inserted ID: {instance_id}")
        
        conn.commit()
        print("Committed.")
        
        # Check immediately with same connection (should work even if not committed if same txn, but we committed)
        cursor.execute("SELECT * FROM process_instances WHERE id = %s", (instance_id,))
        row = cursor.fetchone()
        print(f"Select with same conn: {bool(row)}")
        
        conn.close()
        
        # Check with new connection
        conn2 = connect()
        cursor2 = conn2.cursor()
        cursor2.execute("SELECT * FROM process_instances WHERE id = %s", (instance_id,))
        row2 = cursor2.fetchone()
        print(f"Select with new conn: {bool(row2)}")
        conn2.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_insert()
