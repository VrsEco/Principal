import csv, json, re
from decimal import Decimal
from pathlib import Path

BASE = Path(r'C:\GestaoVersus\app32')
TITLES = BASE / 'outputs' / 'save_water_financial_import_titles_expanded_v2.csv'
SETTLEMENTS = BASE / 'outputs' / 'save_water_financial_import_settlements_expanded_v2.csv'
PREVIEW = BASE / 'outputs' / 'save_water_financial_import_preview.csv'
OUT = BASE / 'tmp' / 'save_water_import_manifest_v1.json'
BATCH_ID = 'conta_azul_save_water_20260525_v1'
COMPANY_ID = 1
COST_CENTER_ID = 23
COST_CENTER_CODE = '7.1'
PAYMENT_METHOD_NAME = 'GERAL'
SOURCE_FILE = 'ContaAzul - Final.xlsx'

CODE_RE = re.compile(r'(\d+(?:\.\d+)+)\s*-')

def s(v):
    if v is None:
        return ''
    return str(v).strip()

def amount_str(v):
    txt = s(v)
    if not txt or txt.lower() == 'nan':
        return None
    return f"{Decimal(txt):.2f}"

preview_by_row = {}
with PREVIEW.open('r', encoding='utf-8-sig', newline='') as f:
    for row in csv.DictReader(f):
        preview_by_row[int(row['excel_row'])] = row

groups = {}
with TITLES.open('r', encoding='utf-8-sig', newline='') as f:
    for row in csv.DictReader(f):
        key = row['title_key']
        grp = groups.setdefault(key, {'title': None, 'allocations': []})
        if row['entity_type'] == 'title':
            grp['title'] = row
        else:
            note = s(row.get('notes'))
            m = CODE_RE.search(note)
            chart_code = m.group(1) if m else None
            alloc = {
                'chart_account_code': chart_code,
                'amount': amount_str(row.get('amount')),
                'note': note,
            }
            if chart_code:
                grp['allocations'].append(alloc)

settlements_by_key = {}
with SETTLEMENTS.open('r', encoding='utf-8-sig', newline='') as f:
    for row in csv.DictReader(f):
        key = row['title_key']
        settlements_by_key.setdefault(key, []).append({
            'component': s(row.get('component')),
            'settlement_date': s(row.get('settlement_date')),
            'bank_account_id': int(s(row.get('bank_account_target_id'))) if s(row.get('bank_account_target_id')) else None,
            'bank_account_name': s(row.get('bank_account_target_name')),
            'amount': amount_str(row.get('amount')),
            'notes': s(row.get('notes')),
        })

entries = []
for key in sorted(groups.keys(), key=lambda k: (int(groups[k]['title']['excel_row']), k)):
    title = groups[key]['title']
    if not title:
        raise SystemExit(f'Título ausente para {key}')
    excel_row = int(title['excel_row'])
    preview = preview_by_row[excel_row]
    title_kind = s(title['title_kind']).lower()
    title_type = 'transfer' if title_kind == 'transfer' else title_kind
    tipo_origem = s(preview.get('tipo_origem')).lower()
    if title_type == 'payable':
        movement_nature = 'debit'
    elif title_type == 'receivable':
        movement_nature = 'credit'
    elif title_type == 'transfer':
        movement_nature = 'credit' if tipo_origem == 'receita' else 'debit'
    else:
        raise SystemExit(f'title_type inesperado: {title_type}')

    allocations = groups[key]['allocations']
    primary_chart_code = allocations[0]['chart_account_code'] if len(allocations) == 1 else None
    entry = {
        'title_key': key,
        'excel_row': excel_row,
        'entry_code': f'CA-SW-{key}',
        'entry_type': title_type,
        'movement_nature': movement_nature,
        'description': s(title['descricao']),
        'counterparty_name': s(title.get('favorecido')),
        'counterparty_document': s(title.get('identificador')),
        'issue_date': s(title.get('issue_date')),
        'competence_date': s(title.get('competence_date')),
        'due_date': s(title.get('due_date')),
        'original_amount': amount_str(title.get('amount')),
        'open_balance_amount': amount_str(title.get('open_balance_amount')),
        'status_original': s(preview.get('situacao')),
        'scenario': s(title.get('scenario')),
        'origin_source_type': s(preview.get('origem_lancamento')),
        'bank_account_source': s(preview.get('settlement_bank_account_source')),
        'payment_method_name': PAYMENT_METHOD_NAME,
        'cost_center_id': COST_CENTER_ID,
        'cost_center_code': COST_CENTER_CODE,
        'primary_chart_account_code': primary_chart_code,
        'allocations': allocations,
        'settlements': settlements_by_key.get(key, []),
        'notes': s(title.get('notes')),
    }
    entries.append(entry)

manifest = {
    'batch_id': BATCH_ID,
    'company_id': COMPANY_ID,
    'source_system': 'conta_azul',
    'source_file': SOURCE_FILE,
    'generated_from': {
        'titles_csv': str(TITLES),
        'settlements_csv': str(SETTLEMENTS),
        'preview_csv': str(PREVIEW),
    },
    'totals': {
        'entries': len(entries),
        'settlements': sum(len(item['settlements']) for item in entries),
        'allocations': sum(len(item['allocations']) for item in entries),
    },
    'entries': entries,
}
OUT.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'ok': True, 'output': str(OUT), 'totals': manifest['totals'], 'sample_entry_codes': [e['entry_code'] for e in entries[:5]]}, ensure_ascii=False, indent=2))
