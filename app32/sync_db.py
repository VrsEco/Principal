from app import create_app
from models import db
from sqlalchemy import inspect, text

app = create_app()
with app.app_context():
    inspector = inspect(db.engine)
    columns = [c['name'] for c in inspector.get_columns('indicator_goals')]
    print(f"COLUMNS: {columns}")
    
    if 'goal_type' not in columns:
        print("Adding goal_type column...")
        db.session.execute(text("ALTER TABLE indicator_goals ADD COLUMN goal_type VARCHAR(50) DEFAULT 'monthly'"))
        db.session.commit()
        print("Column added successfully.")
    else:
        print("goal_type already exists.")
