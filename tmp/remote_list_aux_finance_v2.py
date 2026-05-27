from app import create_app
from models import db
from sqlalchemy import text
import json

COMPANY_ID = 1
queries = {
    'counterparties': "select id, code, name, legal_name, document_number, is_active from financial_counterparties where company_id = :cid and deleted_at is null order by name",
    'chart_accounts': "select id, code, name, movement_nature, accepts_posting, is_active from financial_chart_accounts where company_id = :cid and deleted_at is null order by code, name",
    'cost_centers': "select id, code, name, accepts_posting, is_active from financial_cost_centers where company_id = :cid and deleted_at is null order by code, name",
    'bank_accounts': "select id, code, name, bank_code, bank_name, branch_number, account_number, is_active from financial_bank_accounts where company_id = :cid and deleted_at is null order by name",
    'payment_methods': "select id, code, name, is_default_suggestion, is_active from financial_payment_methods where company_id = :cid and deleted_at is null order by name",
    'account_categories': "select id, code, name, is_active from financial_account_categories where company_id = :cid and deleted_at is null order by code, name"
}
app = create_app('production')
with app.app_context():
    result = {}
    for key, sql in queries.items():
        rows = db.session.execute(text(sql), {'cid': COMPANY_ID}).mappings().all()
        result[key] = [dict(row) for row in rows]
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
