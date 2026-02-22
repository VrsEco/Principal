import sys
import os
sys.path.insert(0, os.getcwd())
from models import db, MacroProcess
from app import app

with app.app_context():
    print("Listing last 10 Macroprocesses:")
    macros = MacroProcess.query.order_by(MacroProcess.id.desc()).limit(10).all()
    for m in macros:
        print(f"ID: {m.id} | Name: {m.name} | Area ID: {m.area_id} | Company ID: {m.company_id} | Code: {m.code}")
