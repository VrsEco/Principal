
from app import create_app
from models import db, Process, Company
from sqlalchemy import func

app = create_app()
with app.app_context():
    stats = db.session.query(Process.company_id, func.count(Process.id)).group_by(Process.company_id).order_by(func.count(Process.id).desc()).limit(10).all()
    for cid, count in stats:
        c = Company.query.get(cid)
        print(f"Company {cid} ({c.name if c else '???'}): {count} processes")
