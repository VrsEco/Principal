
from app import create_app
from database import get_db

app = create_app()
with app.app_context():
    try:
        db_helper = get_db()
        conn = db_helper._get_connection()
        cursor = conn.cursor()
        
        # Check tables related to processes
        tables = ['process_areas', 'macro_processes', 'processes', 'process_routines', 'process_steps', 'process_instances', 'routines', 'routine_collaborators']
        for table in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"Table {table}: {count} rows")
            except Exception as e:
                print(f"Table {table}: Error -> {e}")
                conn.rollback() # Rollback to continue with next tables
                
        # Check columns of process_instances
        cursor.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'process_instances' AND table_schema = 'public'")
        cols = cursor.fetchall()
        print("\nColumns in process_instances:")
        for col in cols:
            print(f" - {col[0]} ({col[1]})")
            
        conn.close()
    except Exception as e:
        print(f"Global Error: {e}")
