import sys
import os
sys.path.insert(0, os.getcwd())
from models import Company
from app import app

with app.app_context():
    c = Company.query.get(5)
    if c:
        print(f"Company 5: Name={c.name}, Code={c.client_code}")
    else:
        print("Company 5 not found")
