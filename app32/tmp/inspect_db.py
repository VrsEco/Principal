import os
import sys

# Define base path
BASE_PATH = r"c:\GestaoVersus\app32"
sys.path.append(BASE_PATH)

from app import create_app
from models import db
from sqlalchemy import inspect

app = create_app()

with app.app_context():
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    
    with open(r"c:\GestaoVersus\app32\tmp\db_inspect_results.txt", "w") as f:
        f.write(f"Tables: {tables}\n\n")
        
        if 'indicators' in tables:
            columns = [c['name'] for c in inspector.get_columns('indicators')]
            f.write(f"Columns in 'indicators': {columns}\n")
        else:
            f.write("'indicators' table not found.\n")
            
        if 'incentive_indicators' in tables:
            columns = [c['name'] for c in inspector.get_columns('incentive_indicators')]
            f.write(f"Columns in 'incentive_indicators': {columns}\n")
        else:
            f.write("'incentive_indicators' table not found.\n")
