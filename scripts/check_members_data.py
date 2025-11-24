import os
import psycopg2
from psycopg2.extras import RealDictCursor

def check_alignment_members(plan_id):
    print(f"--- Checking alignment members for plan_id={plan_id} ---")
    
    # Get DB config from environment or use defaults (matching docker-compose)
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    database = os.environ.get("POSTGRES_DB", "bd_app_versus")
    user = os.environ.get("POSTGRES_USER", "postgres")
    password = os.environ.get("POSTGRES_PASSWORD", "postgres") # Default password often used in dev

    print(f"Connecting to {user}@{host}:{port}/{database}...")

    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password
        )
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Check count
        cursor.execute("SELECT COUNT(*) as count FROM plan_alignment_members WHERE plan_id = %s", (plan_id,))
        count = cursor.fetchone()['count']
        print(f"Total members found: {count}")
        
        if count > 0:
            cursor.execute("""
                SELECT id, name, role, motivation, commitment, risk, created_at 
                FROM plan_alignment_members 
                WHERE plan_id = %s 
                ORDER BY created_at
            """, (plan_id,))
            rows = cursor.fetchall()
            print("\nMembers details:")
            for row in rows:
                print(f" - ID: {row['id']}, Name: {row['name']}, Role: {row['role']}")
        else:
            print("No members found. Checking if table exists and has any data...")
            cursor.execute("SELECT COUNT(*) as total FROM plan_alignment_members")
            total = cursor.fetchone()['total']
            print(f"Total records in table (all plans): {total}")

        conn.close()
        print("\nDone.")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_alignment_members(6)
