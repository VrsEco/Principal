from app import app
from models import db
from sqlalchemy import text, inspect

with app.app_context():
    print(f"Database URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
    
    inspector = inspect(db.engine)
    columns = [c['name'] for c in inspector.get_columns('project_tasks')]
    print(f"Current columns: {columns}")
    
    if 'logs' not in columns:
        print("Attempting to add 'logs' column...")
        try:
            with db.engine.connect() as conn:
                conn.execute(text("ALTER TABLE project_tasks ADD COLUMN logs JSON DEFAULT '[]'"))
                conn.commit()
            print("Successfully added 'logs' column!")
        except Exception as e:
            print(f"Failed to add 'logs' column: {e}")
    else:
        print("'logs' column already exists in inspector results.")

    if 'completion_date' not in columns:
        print("Attempting to add 'completion_date' column...")
        try:
            with db.engine.connect() as conn:
                conn.execute(text("ALTER TABLE project_tasks ADD COLUMN completion_date DATE"))
                conn.commit()
            print("Successfully added 'completion_date' column!")
        except Exception as e:
            print(f"Failed to add 'completion_date' column: {e}")
