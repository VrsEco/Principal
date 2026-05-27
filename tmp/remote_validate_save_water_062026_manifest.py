from __future__ import annotations
import json
import re
import unicodedata
from pathlib import Path
from app import create_app
from models import db

COMPANY_ID = 1
MANIFEST_PATH = Path('tmp/save_water_import_manifest_062026_v1.json')

def norm(value):
    value = '' if value is None else str(value).strip()
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii').lower()
    value = re.sub(r'\s+', ' ', value)
    return value.strip()

app = create_app('production')
with app.app_context():
    manifest = json.loads(MANIFEST_PATH.read_text(encoding='utf-8'))
    cps = db.session.execute(db.text("select id, name, document_number from financial_counterparties where company_id=:cid and deleted_at is null"), {'cid': COMPANY_ID}).mappings().all()
    by_name = {}
    by_doc = {}
    for cp in cps:
        cp=dict(cp)
        by_name.setdefault(norm(cp['name']), []).append(cp)
        doc = ''.join(ch for ch in str(cp.get('document_number') or '') if ch.isdigit())
        if doc:
            by_doc[doc]=cp
    charts = db.session.execute(db.text("select code from financial_chart_accounts where company_id=:cid and deleted_at is null"), {'cid': COMPANY_ID}).scalars().all()
    chart_set = {str(c).strip() for c in charts}
    missing_cp=[]
    missing_chart=[]
    for entry in manifest['entries']:
        doc=''.join(ch for ch in str(entry.get('counterparty_document') or '') if ch.isdigit())
        name=norm(entry.get('counterparty_name'))
        if not ((doc and doc in by_doc) or (name and name in by_name)):
            missing_cp.append({'name': entry.get('counterparty_name'), 'doc': entry.get('counterparty_document')})
        for alloc in entry.get('allocations') or []:
            code=str(alloc.get('chart_account_code') or '').strip()
            if code and code not in chart_set:
                missing_chart.append({'entry_code': entry.get('entry_code'), 'chart_account_code': code})
    uniq_cp=[]
    seen=set()
    for row in missing_cp:
        k=(row['name'], row['doc'])
        if k not in seen:
            seen.add(k)
            uniq_cp.append(row)
    print(json.dumps({
        'entries': len(manifest['entries']),
        'allocations': sum(len(e.get('allocations') or []) for e in manifest['entries']),
        'missing_counterparties_count': len(uniq_cp),
        'missing_counterparties_sample': uniq_cp[:20],
        'missing_chart_count': len(missing_chart),
        'missing_chart_sample': missing_chart[:20],
    }, ensure_ascii=False, indent=2))
