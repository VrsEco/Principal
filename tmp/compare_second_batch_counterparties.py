import json
import pandas as pd
from pathlib import Path
from app import create_app
from models import db

COMPANY_ID = 1
XLS_PATH = Path(r"C:\Users\mff20\OneDrive\Versus\Versus Consultoria\Versus - Clientes\AL - Save Water\Transição ContaAzul - Versus\Conta Azul - Versus - Final 062026.xls")

def norm(v):
    if v is None:
        return ''
    s = str(v).strip().lower()
    return ' '.join(s.split())

def doc_norm(v):
    if pd.isna(v) or v is None:
        return ''
    raw = str(v).strip()
    if raw.endswith('.0'):
        raw = raw[:-2]
    return ''.join(ch for ch in raw if ch.isdigit())

app = create_app('production')
with app.app_context():
    df = pd.read_excel(XLS_PATH, sheet_name='Extrato Financeiro')
    sheet_rows = []
    for _, r in df.iterrows():
        name = str(r['Nome do fornecedor/cliente']).strip() if pd.notna(r['Nome do fornecedor/cliente']) else ''
        doc = doc_norm(r['Identificador do fornecedor/cliente'])
        if name:
            sheet_rows.append((norm(name), name, doc))
    uniq = {}
    for nk, name, doc in sheet_rows:
        uniq.setdefault((nk, doc), {'name': name, 'doc': doc})

    cps = db.session.execute(db.text("select id, name, document_number from financial_counterparties where company_id=:cid and deleted_at is null"), {'cid': COMPANY_ID}).mappings().all()
    by_name = {}
    by_doc = {}
    for cp in cps:
        cp = dict(cp)
        by_name.setdefault(norm(cp['name']), []).append(cp)
        d = doc_norm(cp['document_number'])
        if d:
            by_doc[d] = cp

    missing = []
    matched = 0
    for (_, doc), item in uniq.items():
        nk = norm(item['name'])
        if doc and doc in by_doc:
            matched += 1
            continue
        if nk in by_name:
            matched += 1
            continue
        missing.append(item)

    print(json.dumps({'unique_sheet_counterparties': len(uniq), 'matched': matched, 'missing_count': len(missing), 'missing_sample': missing[:20]}, ensure_ascii=False, indent=2))
