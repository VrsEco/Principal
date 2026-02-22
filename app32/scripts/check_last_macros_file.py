import sys
import os
sys.path.insert(0, os.getcwd())
from models import db, MacroProcess
from app import app

with app.app_context():
    with open('last_macros.txt', 'w', encoding='utf-8') as f:
        f.write("Listing last 10 Macroprocesses:\n")
        macros = MacroProcess.query.order_by(MacroProcess.id.desc()).limit(10).all()
        for m in macros:
            f.write(f"ID: {m.id} | Name: {m.name} | Area ID: {m.area_id} | Company ID: {m.company_id} | Code: {m.code}\n")
