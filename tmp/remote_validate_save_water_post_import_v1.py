from app import create_app
from models import db
from sqlalchemy import text
import json

COMPANY_ID = 1
BATCH_ID = "conta_azul_save_water_20260525_v1"

app = create_app('production')
with app.app_context():
    batch_filter_entries = "fe.metadata_json->>'migration_batch_id' = :batch_id"
    batch_filter_settlements = "fs.metadata_json->>'migration_batch_id' = :batch_id"

    summary = {}
    summary['entries_by_type_status'] = [dict(r) for r in db.session.execute(text("""
        select fe.entry_type, fe.status, count(*) as qty, round(sum(fe.original_amount)::numeric, 2) as total
        from financial_entries fe
        where fe.company_id = :cid and fe.deleted_at is null and fe.metadata_json->>'migration_batch_id' = :batch_id
        group by fe.entry_type, fe.status
        order by fe.entry_type, fe.status
    """), {'cid': COMPANY_ID, 'batch_id': BATCH_ID}).mappings().all()]

    summary['open_entries_by_type'] = [dict(r) for r in db.session.execute(text("""
        select fe.entry_type, count(*) as qty, round(sum(fe.original_amount)::numeric, 2) as total
        from financial_entries fe
        where fe.company_id = :cid and fe.deleted_at is null and fe.metadata_json->>'migration_batch_id' = :batch_id
          and fe.status <> 'settled'
        group by fe.entry_type
        order by fe.entry_type
    """), {'cid': COMPANY_ID, 'batch_id': BATCH_ID}).mappings().all()]

    summary['settlements_by_bank'] = [dict(r) for r in db.session.execute(text("""
        select coalesce(fba.name, '[sem conta]') as bank_account,
               count(*) as qty,
               round(sum(fs.principal_amount)::numeric, 2) as total
        from financial_settlements fs
        left join financial_bank_accounts fba on fba.id = fs.bank_account_id and fba.company_id = fs.company_id
        where fs.company_id = :cid and fs.deleted_at is null and fs.metadata_json->>'migration_batch_id' = :batch_id
        group by coalesce(fba.name, '[sem conta]')
        order by total desc
    """), {'cid': COMPANY_ID, 'batch_id': BATCH_ID}).mappings().all()]

    summary['retentions'] = [dict(r) for r in db.session.execute(text("""
        select fe.entry_type,
               count(*) as qty,
               round(sum(fe.original_amount)::numeric, 2) as total_titles
        from financial_entries fe
        where fe.company_id = :cid and fe.deleted_at is null
          and fe.metadata_json->>'migration_batch_id' = :batch_id
          and (fe.metadata_json->>'scenario') like 'withholding_%'
        group by fe.entry_type
        order by fe.entry_type
    """), {'cid': COMPANY_ID, 'batch_id': BATCH_ID}).mappings().all()]

    summary['retention_settlements_compensation'] = [dict(r) for r in db.session.execute(text("""
        select fe.entry_type,
               count(*) as qty,
               round(sum(fs.principal_amount)::numeric, 2) as total
        from financial_settlements fs
        join financial_entries fe on fe.id = fs.financial_entry_id and fe.company_id = fs.company_id
        where fs.company_id = :cid and fs.deleted_at is null
          and fs.metadata_json->>'migration_batch_id' = :batch_id
          and fs.bank_account_id = 12
          and (fe.metadata_json->>'scenario') like 'withholding_%'
        group by fe.entry_type
        order by fe.entry_type
    """), {'cid': COMPANY_ID, 'batch_id': BATCH_ID}).mappings().all()]

    summary['transfers'] = [dict(r) for r in db.session.execute(text("""
        select fe.entry_code, fe.description, fe.movement_nature, fe.status, fe.original_amount
        from financial_entries fe
        where fe.company_id = :cid and fe.deleted_at is null and fe.metadata_json->>'migration_batch_id' = :batch_id
          and fe.entry_type = 'transfer'
        order by fe.entry_code
    """), {'cid': COMPANY_ID, 'batch_id': BATCH_ID}).mappings().all()]

    summary['classification_pending'] = [dict(r) for r in db.session.execute(text("""
        select fe.entry_code, fe.description, fe.entry_type, fe.status, fe.original_amount
        from financial_entries fe
        where fe.company_id = :cid and fe.deleted_at is null and fe.metadata_json->>'migration_batch_id' = :batch_id
          and coalesce((fe.metadata_json->>'classification_pending')::boolean, false) = true
        order by fe.entry_code
    """), {'cid': COMPANY_ID, 'batch_id': BATCH_ID}).mappings().all()]

    summary['receivables_payables_snapshot'] = [dict(r) for r in db.session.execute(text("""
        select fe.entry_type,
               count(*) as qty,
               round(sum(fe.original_amount)::numeric, 2) as total_titles,
               round(sum(case when fe.status = 'settled' then fe.original_amount else 0 end)::numeric, 2) as settled_titles,
               round(sum(case when fe.status <> 'settled' then fe.original_amount else 0 end)::numeric, 2) as open_titles
        from financial_entries fe
        where fe.company_id = :cid and fe.deleted_at is null and fe.metadata_json->>'migration_batch_id' = :batch_id
          and fe.entry_type in ('payable','receivable')
        group by fe.entry_type
        order by fe.entry_type
    """), {'cid': COMPANY_ID, 'batch_id': BATCH_ID}).mappings().all()]

    print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
