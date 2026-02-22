
from app import create_app
from models import db, Process, Company
app = create_app()
with app.app_context():
    with open('real_results.txt', 'w') as f:
        f.write("COUNT AUDIT\n")
        for cid in [1, 5, 14, 36, 37]:
            c = Company.query.get(cid)
            count = Process.query.filter_by(company_id=cid).count()
            f.write(f"[{cid}] {c.name if c else '???'}: {count} processes\n")
