from app import create_app
from models import db
from sqlalchemy import text
import json
app = create_app('production')
with app.app_context():
    rows = db.session.execute(text("""
        select id, code, name, accepts_posting
        from financial_chart_accounts
        where company_id = :cid and deleted_at is null
          and (lower(name) like :q1 or lower(name) like :q2 or code like :q3)
        order by code
    """), {'cid': 1, 'q1': '%compensa%', 'q2': '%reten%', 'q3': '999%'}).mappings().all()
    print(json.dumps([dict(r) for r in rows], ensure_ascii=False, indent=2, default=str))
