from app import create_app
from models import db
from sqlalchemy import text
import json

TABLES = [
    'financial_counterparties',
    'financial_chart_accounts',
    'financial_cost_centers',
    'financial_bank_accounts',
    'financial_payment_methods',
    'financial_account_categories'
]
app = create_app('production')
with app.app_context():
    result = {}
    for table in TABLES:
        cols = db.session.execute(text("""
            select column_name
            from information_schema.columns
            where table_schema = 'public' and table_name = :table
            order by ordinal_position
        """), {'table': table}).scalars().all()
        result[table] = cols
    print(json.dumps(result, ensure_ascii=False, indent=2))
