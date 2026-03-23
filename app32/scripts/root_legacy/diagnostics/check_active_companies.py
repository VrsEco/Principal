
from app import create_app
from models import db, Process, Company
from sqlalchemy import func

app = create_app()
with app.app_context():
    # Only companies with processes
    stats = db.session.query(Process.company_id, func.count(Process.id)).group_by(Process.company_id).all()
    print("COMPANIES WITH PROCESSES:")
    for cid, count in stats:
        c = Company.query.get(cid)
        name = c.name if c else "???"
        print(f"[{cid}] {name}: {count} processes")
