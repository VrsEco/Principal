from app import app
from models import db
from sqlalchemy import inspect

with app.app_context():
    inspector = inspect(db.engine)
    print("--- ROLES ---")
    columns = inspector.get_columns('roles')
    for column in columns:
        print(f"{column['name']}: {column['type']}")

    print("--- SETTINGS ---")
    columns_settings = inspector.get_columns('company_performance_settings')
    for column in columns_settings:
        print(f"{column['name']}: {column['type']}")
