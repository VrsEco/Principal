from app import create_app
from models import db
import sqlalchemy

app = create_app()
with app.app_context():
    inspector = sqlalchemy.inspect(db.engine)
    columns = [c['name'] for c in inspector.get_columns('incentive_calculations')]
    print(f"Columns: {columns}")
    
    if 'results_payload' not in columns:
        print("Adding column results_payload...")
        with db.engine.connect() as conn:
            conn.execute(sqlalchemy.text("ALTER TABLE incentive_calculations ADD COLUMN results_payload JSON"))
            conn.commit()
        print("Column added successfully.")
    else:
        print("Column already exists.")
