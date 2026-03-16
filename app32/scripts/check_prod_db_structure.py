
import os, sys
sys.path.append(os.getcwd())
from app import create_app
from sqlalchemy import text, inspect

app = create_app()
with app.app_context():
    from models import db
    inspector = inspect(db.engine)
    
    tables = [
        "incentive_indicators",
        "indicator_goals",
        "indicator_groups",
        "incentive_indicator_tree"
    ]
    
    for table in tables:
        print(f"Checking table: {table}")
        if not inspector.has_table(table):
            print(f"  Table {table} DOES NOT EXIST")
            continue
            
        columns = inspector.get_columns(table)
        for col in columns:
            print(f"  Column: {col['name']} ({col['type']})")
            
        fks = inspector.get_foreign_keys(table)
        for fk in fks:
            print(f"  FK: {fk['constrained_columns']} -> {fk['referred_table']}.{fk['referred_columns']}")
        print("-" * 20)
