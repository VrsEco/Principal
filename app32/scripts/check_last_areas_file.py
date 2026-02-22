import sys
import os
sys.path.insert(0, os.getcwd())
from models import db, ProcessArea
from app import app

with app.app_context():
    with open('last_areas.txt', 'w', encoding='utf-8') as f:
        f.write("Listing last 20 Process Areas:\n")
        areas = ProcessArea.query.order_by(ProcessArea.id.desc()).limit(20).all()
        for a in areas:
            f.write(f"ID: {a.id} | Name: {a.name} | Company ID: {a.company_id} | Code: {a.code}\n")
