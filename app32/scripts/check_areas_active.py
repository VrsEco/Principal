import sys
import os
sys.path.insert(0, os.getcwd())
from models import db, ProcessArea
from app import app

with app.app_context():
    areas = ProcessArea.query.filter_by(company_id=5).all()
    print(f"Total areas for Company 5: {len(areas)}")
    for a in areas:
        print(f"ID: {a.id} | Name: {a.name} | Active: {a.is_active} | Code: {a.code}")
