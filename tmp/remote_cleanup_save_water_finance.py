from app import create_app
from models import db
from sqlalchemy import text
from datetime import datetime
import json

COMPANY_ID = 1
SOFT_DELETE_TABLES = [
    'financial_reconciliation_matches',
    'financial_classification_suggestions',
    'financial_import_rows',
    'financial_import_batches',
    'financial_ingestion_records',
    'financial_title_adjustments',
    'financial_settlements',
    'financial_entry_allocations',
    'financial_entries',
    'financial_bordero_items',
    'financial_bordero_settlements',
    'financial_borderos',
    'financial_schedules'
]
HARD_DELETE_TABLES = [
    'financial_settlement_components',
    'financial_title_adjustment_allocations',
    'financial_title_calculation_logs'
]

app = create_app('production')
with app.app_context():
    before = {}
    for table in HARD_DELETE_TABLES:
        before[table] = db.session.execute(
            text(f"select count(*) from {table} where company_id = :cid"),
            {'cid': COMPANY_ID},
        ).scalar_one()
    for table in SOFT_DELETE_TABLES:
        before[table] = db.session.execute(
            text(f"select count(*) from {table} where company_id = :cid and deleted_at is null"),
            {'cid': COMPANY_ID},
        ).scalar_one()

    now = datetime.utcnow()
    hard_deleted = {}
    soft_deleted = {}

    for table in HARD_DELETE_TABLES:
        result = db.session.execute(
            text(f"delete from {table} where company_id = :cid"),
            {'cid': COMPANY_ID},
        )
        hard_deleted[table] = result.rowcount or 0

    for table in SOFT_DELETE_TABLES:
        result = db.session.execute(
            text(f"update {table} set deleted_at = :now, updated_at = :now where company_id = :cid and deleted_at is null"),
            {'cid': COMPANY_ID, 'now': now},
        )
        soft_deleted[table] = result.rowcount or 0

    db.session.commit()

    after = {}
    for table in HARD_DELETE_TABLES:
        after[table] = db.session.execute(
            text(f"select count(*) from {table} where company_id = :cid"),
            {'cid': COMPANY_ID},
        ).scalar_one()
    for table in SOFT_DELETE_TABLES:
        after[table] = db.session.execute(
            text(f"select count(*) from {table} where company_id = :cid and deleted_at is null"),
            {'cid': COMPANY_ID},
        ).scalar_one()

    print(json.dumps({
        'company_id': COMPANY_ID,
        'hard_delete_tables': HARD_DELETE_TABLES,
        'soft_delete_tables': SOFT_DELETE_TABLES,
        'before': before,
        'hard_deleted': hard_deleted,
        'soft_deleted': soft_deleted,
        'after': after,
        'processed_at_utc': now.isoformat(),
    }, ensure_ascii=False, indent=2))
