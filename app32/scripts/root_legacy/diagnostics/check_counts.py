
import os
from app import create_app
from models import db, Process, Company
from sqlalchemy import func

app = create_app()
with app.app_context():
    stats = db.session.query(Process.company_id, func.count(Process.id)).group_by(Process.company_id).all()
    print("Process counts by company:")
    for cid, count in stats:
        name = Company.query.get(cid).name if Company.query.get(cid) else "Unknown"
        print(f"Company {cid} ({name}): {count}")
    
    # Check routines too
    from models.process import ProcessRoutine
    r_count = ProcessRoutine.query.count()
    print(f"Total routines (process_routines table): {r_count}")
    
    # Check 'routines' table via raw SQL if needed, but let's check the model
    # The models.py might have multiple models for routines
