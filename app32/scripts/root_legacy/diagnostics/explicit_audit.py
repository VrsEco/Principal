
from app import create_app
from models import db, Process, Company
app = create_app()
with app.app_context():
    print("COUNT AUDIT")
    for cid in [1, 5, 14, 36, 37]:
        c = Company.query.get(cid)
        count = Process.query.filter_by(company_id=cid).count()
        print(f"[{cid}] {c.name if c else '???'}: {count} processes")
