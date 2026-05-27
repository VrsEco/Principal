from app import create_app
from models import db
from sqlalchemy import text
from datetime import datetime
import json
import re
import unicodedata

COMPANY_ID = 1
KEEP_AGRO_ID = 9
DELETE_AGRO_IDS = [10, 11]
PAYLOAD_PATH = 'tmp/missing_counterparties.json'
CODE_PREFIX = 'MIG.CA.'


def norm(value):
    value = '' if value is None else str(value).strip()
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii').lower()
    value = re.sub(r'\s+', ' ', value)
    return value.strip()

app = create_app('production')
with app.app_context():
    payload = json.load(open(PAYLOAD_PATH, 'r', encoding='utf-8'))

    existing = db.session.execute(text("""
        select id, code, name, legal_name, document_number
        from financial_counterparties
        where company_id = :cid and deleted_at is null
        order by id
    """), {'cid': COMPANY_ID}).mappings().all()

    existing_by_doc = {}
    existing_by_name = {}
    for row in existing:
        rowd = dict(row)
        if rowd['document_number']:
            existing_by_doc[norm(rowd['document_number'])] = rowd
        existing_by_name.setdefault(norm(rowd['name']), []).append(rowd)

    now = datetime.utcnow()

    agro_before = db.session.execute(text("""
        select id, code, name, document_number, deleted_at
        from financial_counterparties
        where company_id = :cid and upper(name) = 'AGROQUIMICA'
        order by id
    """), {'cid': COMPANY_ID}).mappings().all()

    agro_deleted = 0
    if DELETE_AGRO_IDS:
        agro_deleted = db.session.execute(text("""
            update financial_counterparties
               set deleted_at = :now,
                   updated_at = :now,
                   notes = coalesce(notes, '') || case when coalesce(notes, '') = '' then '' else E'\n' end || '[Codex] Consolidado em favor do cadastro ID ' || :keep_id
             where company_id = :cid
               and id = any(:ids)
               and deleted_at is null
        """), {'cid': COMPANY_ID, 'ids': DELETE_AGRO_IDS, 'now': now, 'keep_id': str(KEEP_AGRO_ID)}).rowcount or 0

    existing_codes = set(
        db.session.execute(text("select code from financial_counterparties where company_id = :cid"), {'cid': COMPANY_ID}).scalars().all()
    )

    def next_code(seq_num):
        return f'{CODE_PREFIX}{seq_num:03d}'

    seq = 1
    created = []
    skipped = []
    for item in payload:
        doc = norm(item.get('document_number'))
        name = norm(item['name'])
        matched = None
        if doc and doc in existing_by_doc:
            matched = existing_by_doc[doc]
        elif name in existing_by_name:
            lst = existing_by_name[name]
            if len(lst) == 1:
                matched = lst[0]
        if matched:
            skipped.append({'source': item, 'reason': 'already_exists', 'target_id': matched['id']})
            continue

        while next_code(seq) in existing_codes:
            seq += 1
        code = next_code(seq)
        existing_codes.add(code)
        seq += 1

        new_id = db.session.execute(text("""
            insert into financial_counterparties (
                company_id, default_chart_account_id, default_cost_center_id,
                code, name, legal_name, document_number, email, phone, pix_key,
                notes, is_active, metadata_json, created_at, updated_at, deleted_at
            ) values (
                :company_id, null, null,
                :code, :name, :legal_name, :document_number, null, null, null,
                :notes, true, cast(:metadata_json as jsonb), :created_at, :updated_at, null
            )
            returning id
        """), {
            'company_id': COMPANY_ID,
            'code': code,
            'name': item['name'].strip(),
            'legal_name': item['name'].strip(),
            'document_number': (item.get('document_number') or None),
            'notes': f"[Migração Conta Azul] criado automaticamente a partir da planilha final; ocorrências={item.get('count', 0)}",
            'metadata_json': json.dumps({'migration_source': 'conta_azul_final_xlsx', 'source': 'codex', 'occurrences': item.get('count', 0)}, ensure_ascii=False),
            'created_at': now,
            'updated_at': now,
        }).scalar_one()
        created.append({'id': new_id, 'code': code, 'name': item['name'], 'document_number': item.get('document_number')})
        newrow = {'id': new_id, 'code': code, 'name': item['name'], 'legal_name': item['name'], 'document_number': item.get('document_number')}
        if item.get('document_number'):
            existing_by_doc[norm(item['document_number'])] = newrow
        existing_by_name.setdefault(norm(item['name']), []).append(newrow)

    db.session.commit()

    agro_after = db.session.execute(text("""
        select id, code, name, document_number, deleted_at
        from financial_counterparties
        where company_id = :cid and upper(name) = 'AGROQUIMICA'
        order by id
    """), {'cid': COMPANY_ID}).mappings().all()

    total_active = db.session.execute(text("""
        select count(*)
        from financial_counterparties
        where company_id = :cid and deleted_at is null
    """), {'cid': COMPANY_ID}).scalar_one()

    print(json.dumps({
        'company_id': COMPANY_ID,
        'agro_before': [dict(r) for r in agro_before],
        'agro_deleted_count': agro_deleted,
        'agro_after': [dict(r) for r in agro_after],
        'created_count': len(created),
        'skipped_count': len(skipped),
        'created_preview': created[:20],
        'total_active_counterparties': total_active,
        'processed_at_utc': now.isoformat(),
    }, ensure_ascii=False, indent=2, default=str))
