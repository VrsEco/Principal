from app import create_app
from models import db
from sqlalchemy import text
from datetime import datetime
import json

COMPANY_ID = 1
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
    before = {}
    for table in TABLES:
        before[table] = db.session.execute(
            text(f"select count(*) from {table} where company_id = :cid and deleted_at is null"),
            {'cid': COMPANY_ID},
        ).scalar_one()

    now = datetime.utcnow()
    affected = {}
    for table in TABLES:
        result = db.session.execute(
            text(f"update {table} set deleted_at = :now, updated_at = :now where company_id = :cid and deleted_at is null"),
            {'cid': COMPANY_ID, 'now': now},
        )
        affected[table] = result.rowcount or 0

    db.session.commit()

    after = {}
    for table in TABLES:
        after[table] = db.session.execute(
            text(f"select count(*) from {table} where company_id = :cid and deleted_at is null"),
            {'cid': COMPANY_ID},
        ).scalar_one()

    print(json.dumps({
        'company_id': COMPANY_ID,
        'before': before,
        'affected': affected,
        'after': after,
        'deleted_at_utc': now.isoformat(),
    }, ensure_ascii=False, indent=2))
