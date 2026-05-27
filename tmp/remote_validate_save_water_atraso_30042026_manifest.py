from __future__ import annotations
import json, re, unicodedata
from app import create_app
from models import db

COMPANY_ID = 1
MANIFEST_PATH = 'tmp/save_water_import_manifest_atraso_30042026_v1.json'

def norm(v):
    v = '' if v is None else str(v).strip()
    v = unicodedata.normalize('NFKD', v).encode('ascii', 'ignore').decode('ascii').lower()
    return re.sub(r'\s+', ' ', v).strip()

def digits(v):
    return ''.join(ch for ch in str(v or '') if ch.isdigit())

app = create_app('production')
with app.app_context():
    manifest = json.loads(open(MANIFEST_PATH, encoding='utf-8').read())
    cps = db.session.execute(db.text("select id,name,document_number from financial_counterparties where company_id=:cid and deleted_at is null"), {'cid': COMPANY_ID}).mappings().all()
    charts = set(str(x).strip() for x in db.session.execute(db.text("select code from financial_chart_accounts where company_id=:cid and deleted_at is null"), {'cid': COMPANY_ID}).scalars().all())
    by_name = {}
    by_doc = {}
    for cp in cps:
        cp=dict(cp)
        by_name.setdefault(norm(cp['name']), []).append(cp)
        doc = digits(cp.get('document_number'))
        if doc:
            by_doc[doc]=cp
    miss_cp=[]
    miss_chart=[]
    for e in manifest['entries']:
        doc=digits(e.get('counterparty_document'))
        name=norm(e.get('counterparty_name'))
        if not ((doc and doc in by_doc) or (name and name in by_name)):
            miss_cp.append({'name': e.get('counterparty_name'), 'doc': e.get('counterparty_document')})
        for a in e.get('allocations') or []:
            code = str(a.get('chart_account_code') or '').strip()
            if code and code not in charts:
                miss_chart.append(code)
    uniq=[]; seen=set()
    for r in miss_cp:
        k=(r['name'], r['doc'])
        if k not in seen:
            seen.add(k); uniq.append(r)
    print(json.dumps({'entries': len(manifest['entries']), 'missing_counterparties': uniq, 'missing_chart_codes': sorted(set(miss_chart))}, ensure_ascii=False, indent=2))
