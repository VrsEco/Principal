from app import create_app
from models import db
from sqlalchemy import text
import json

app = create_app('production')
with app.app_context():
    companies = db.session.execute(text("""
        select id, name
        from companies
        where name ilike :term
        order by id
    """), {"term": "%Save Water%"}).mappings().all()
    target = db.session.execute(text("""
        select id, name
        from companies
        where name = :name
        limit 1
    """), {"name": "AY - Save Water"}).mappings().first()

    result = {
        "companies": [dict(row) for row in companies],
        "target": dict(target) if target else None,
        "counts": None,
    }

    if target:
        cid = target["id"]
        tables = [
            "financial_schedules",
            "financial_entries",
            "financial_entry_allocations",
            "financial_settlements",
            "financial_settlement_components",
            "financial_title_adjustments",
            "financial_title_adjustment_allocations",
            "financial_title_calculation_logs",
            "financial_borderos",
            "financial_bordero_items",
            "financial_bordero_settlements",
            "financial_import_batches",
            "financial_import_rows",
            "financial_reconciliation_matches",
            "financial_classification_suggestions",
            "financial_ingestion_records"
        ]
        counts = {}
        for table in tables:
            count = db.session.execute(
                text(f"select count(*) as total from {table} where company_id = :cid and deleted_at is null"),
                {"cid": cid},
            ).scalar_one()
            counts[table] = count
        result["counts"] = counts

    print(json.dumps(result, ensure_ascii=False, indent=2))
