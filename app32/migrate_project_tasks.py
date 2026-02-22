from app import app
from models import db
from sqlalchemy import text

def migrate():
    with app.app_context():
        # Check current columns to avoid errors
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        columns = [c['name'] for c in inspector.get_columns('project_tasks')]
        
        queries = []
        
        if 'stage' not in columns:
            queries.append("ALTER TABLE project_tasks ADD COLUMN stage VARCHAR(50) DEFAULT 'inbox'")
        
        if 'priority' not in columns:
            queries.append("ALTER TABLE project_tasks ADD COLUMN priority VARCHAR(20) DEFAULT 'normal'")
            
        if 'score_weight' not in columns:
            queries.append("ALTER TABLE project_tasks ADD COLUMN score_weight NUMERIC(10, 2) DEFAULT 1")
            
        if 'estimated_hours' not in columns:
            queries.append("ALTER TABLE project_tasks ADD COLUMN estimated_hours NUMERIC(10, 2) DEFAULT 0")
            
        if 'worked_hours' not in columns:
            queries.append("ALTER TABLE project_tasks ADD COLUMN worked_hours NUMERIC(10, 2) DEFAULT 0")
            
        if 'completion_date' not in columns:
            queries.append("ALTER TABLE project_tasks ADD COLUMN completion_date DATE")
            
        if not queries:
            print("No migration needed.")
            return

        print(f"Executing {len(queries)} migration queries...")
        with db.engine.connect() as conn:
            for query in queries:
                print(f"Running: {query}")
                conn.execute(text(query))
            conn.commit()
        print("Migration completed successfully.")

if __name__ == "__main__":
    migrate()
