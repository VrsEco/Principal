from app import create_app
from models import db
from sqlalchemy import text
import json

TABLES = [
    'financial_reconciliation_matches',
    'financial_classification_suggestions',
    'financial_import_rows',
    'financial_import_batches',
    'financial_ingestion_records',
    'financial_settlement_components',
    'financial_title_adjustment_allocations',
    'financial_title_adjustments',
    'financial_title_calculation_logs',
    'financial_settlements',
    'financial_entry_allocations',
    'financial_entries',
    'financial_bordero_items',
    'financial_bordero_settlements',
    'financial_borderos',
    'financial_schedules'
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
