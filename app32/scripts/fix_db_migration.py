from app import create_app, db
from sqlalchemy import text

app = create_app()
with app.app_context():
    # Check columns
    res = db.session.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'process_routines'"))
    columns = [r[0] for r in res]
    print(f"Columns in process_routines: {columns}")
    
    required_columns = {
        'company_id': 'INTEGER',
        'process_id': 'INTEGER',
        'code': 'VARCHAR(50)',
        'name': 'VARCHAR(255)',
        'description': 'TEXT',
        'order_index': 'INTEGER DEFAULT 0',
        'is_active': 'BOOLEAN DEFAULT TRUE',
        'created_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
    }
    
    for col, col_type in required_columns.items():
        if col not in columns:
            print(f"Adding {col} column to process_routines...")
            db.session.execute(text(f"ALTER TABLE process_routines ADD COLUMN {col} {col_type}"))
            db.session.commit()
            print(f"Column {col} added successfully.")
        else:
            print(f"Column {col} already exists.")
