import json, re, unicodedata
from pathlib import Path

def read_any(path):
    data = Path(path).read_bytes()
    for enc in ('utf-8','utf-8-sig','cp1252','latin-1'):
        try:
            return data.decode(enc)
        except Exception:
            continue
    return data.decode('utf-8', errors='ignore')

aux_path = r'C:\GestaoVersus\app32\tmp\contaazul_aux.json'
remote_raw_path = r'C:\GestaoVersus\app32\tmp\remote_aux_finance_raw.txt'
remote_raw = read_any(remote_raw_path)
start = remote_raw.find('{')
remote = json.loads(remote_raw[start:])
aux = json.loads(read_any(aux_path))

def norm(s):
    s = '' if s is None else str(s).strip()
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode('ascii').lower()
    s = re.sub(r'\s+', ' ', s)
    return s.strip()

def normalize_category_name(name):
    n = norm(name)
    for a,b in {
        'alguel':'aluguel',
        'matrial':'material',
        'manutencoes':'manutencao',
        'operacao':'operacao',
    }.items():
        n = n.replace(a,b)
    return n

existing_cp_by_doc = {}
existing_cp_by_name = {}
for cp in remote['counterparties']:
    if cp.get('document_number'):
        existing_cp_by_doc[norm(cp['document_number'])] = cp
    existing_cp_by_name.setdefault(norm(cp['name']), []).append(cp)

missing_cp, matched_cp, ambiguous_cp = [], [], []
for cp in aux['counterparties']:
    doc = norm(cp.get('document_number'))
    name = norm(cp['name'])
    matched = None
    reason = None
    if doc and doc in existing_cp_by_doc:
        matched = existing_cp_by_doc[doc]; reason = 'document_number'
    elif name in existing_cp_by_name:
        lst = existing_cp_by_name[name]
        if len(lst) == 1:
            matched = lst[0]; reason = 'name'
        else:
            ambiguous_cp.append({'source': cp, 'matches': lst, 'reason': 'duplicate_name'}); continue
    if matched: matched_cp.append({'source': cp, 'target': matched, 'reason': reason})
    else: missing_cp.append(cp)

existing_accounts = [a for a in remote['chart_accounts'] if a.get('accepts_posting')]
accounts_by_code = {norm(a['code']): a for a in existing_accounts}
accounts_by_name = {}
for a in existing_accounts:
    accounts_by_name.setdefault(normalize_category_name(a['name']), []).append(a)

explicit_code_map = {
    '3.01.001': '3.01.001','3.02.001': '3.02.001','3.05.001': '3.03.001',
    '4.01.001': '6.1.001','4.01.002': '6.1.002','4.01.004': '6.1.004',
    '5.01.001': '7.1.001','5.01.003': '7.1.003','5.01.004': '7.1.004','5.01.005': '7.1.005','5.01.009': '7.1.009','5.01.011': '7.1.011','5.01.012': '7.1.012',
    '5.02.002': '7.2.002','5.02.003': '7.2.003','5.02.004': '7.2.004','5.02.008': '7.2.008','5.02.999': '7.2.009',
    '5.03.003': '7.3.003','5.04.001': '7.4.001',
    '5.05.002': '7.5.002','5.05.003': '7.5.003','5.05.004': '7.5.004','5.05.005': '7.5.005','5.05.999': '7.5.007',
    '6.01.001': '4.01.001','6.01.002': '4.01.002','6.01.003': '4.01.003','6.01.004': '4.01.004',
    '7.01.001': '8.1.001','7.01.003': '8.1.003','7.01.004': '8.1.004','7.01.012': '8.1.012',
    '7.02.004': '8.2.004','7.03.001': '8.3.001','7.03.008': '8.3.008','7.03.010': '8.3.010','7.03.011': '8.3.011','7.03.012': '8.3.012','7.03.013': '8.3.013','7.03.999': '8.3.015',
    '7.04.999': '8.4.002','7.05.002': '8.5.002','7.06.001': '8.6.001','8.02.001': '9.2.001'
}
category_map=[]; unmapped=[]
for cat in aux['categories']:
    src_code = cat['source_code']; src_name_norm = normalize_category_name(cat['source_name'])
    target=None; reason=None
    if src_code in explicit_code_map:
        target = accounts_by_code.get(norm(explicit_code_map[src_code])); reason='explicit_code_map'
    if target is None:
        lst = accounts_by_name.get(src_name_norm, [])
        if len(lst)==1:
            target=lst[0]; reason='normalized_name'
    if target:
        category_map.append({'source': cat, 'target': target, 'reason': reason})
    else:
        unmapped.append({'source': cat, 'reason': 'skip_transfer' if 'transferencia' in src_name_norm or 'compensacao' in src_name_norm else 'no_match'})

result = {'summary': {'spreadsheet_counterparties': len(aux['counterparties']), 'matched_counterparties': len(matched_cp), 'missing_counterparties': len(missing_cp), 'ambiguous_counterparties': len(ambiguous_cp), 'spreadsheet_categories': len(aux['categories']), 'mapped_categories': len(category_map), 'unmapped_categories': len(unmapped)}, 'missing_counterparties': missing_cp, 'ambiguous_counterparties': ambiguous_cp, 'unmapped_categories': unmapped, 'category_map': category_map}
print(json.dumps(result, ensure_ascii=False, indent=2))
