from app import app
from models import db
from sqlalchemy import inspect

with app.app_context():
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    print("TABLES IN DATABASE:")
    for table in sorted(tables):
        print(f"  - {table}")
