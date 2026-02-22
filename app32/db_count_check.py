
from app import create_app
from models import db, ProcessArea, MacroProcess, Process, Company, Plan

app = create_app()
with app.app_context():
    cid = 5
    area_count = ProcessArea.query.count()
    macro_count = MacroProcess.query.count()
    process_count = Process.query.count()
    
    print(f"Company {cid}:")
    print(f"  Areas: {area_count}")
    print(f"  Macros: {macro_count}")
    print(f"  Processes: {process_count}")
    
    if area_count > 0:
        areas = ProcessArea.query.filter_by(company_id=cid).all()
        for a in areas:
            print(f"    - Area: {a.name} (ID: {a.id})")
