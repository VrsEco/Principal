from database.postgres_helper import connect
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_instance():
    try:
        conn = connect()
        cursor = conn.cursor()
        
        # List all instances
        cursor.execute("SELECT id, instance_code, title, created_at FROM process_instances ORDER BY id DESC LIMIT 10")
        rows = cursor.fetchall()
        print(f"Found {len(rows)} instances:")
        for r in rows:
            print(dict(r))
            
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_instance()
