import sys
import os
sys.path.insert(0, os.getcwd())
from models import db, ProcessArea
from app import app

with app.app_context():
    print("Listing last 10 Process Areas:")
    areas = ProcessArea.query.order_by(ProcessArea.id.desc()).limit(10).all()
    for a in areas:
        print(f"ID: {a.id} | Name: {a.name} | Company ID: {a.company_id} | Code: {a.code}")
