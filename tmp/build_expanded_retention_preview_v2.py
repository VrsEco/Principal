import csv, json, re, unicodedata
from collections import defaultdict, Counter
from pathlib import Path

BASE = Path(r'C:\GestaoVersus\app32')
OUT = BASE / 'outputs'
preview_path = OUT / 'save_water_financial_import_preview.csv'
rateio_path = OUT / 'save_water_financial_import_rateio.csv'

with open(preview_path, newline='', encoding='utf-8-sig') as f:
    preview_rows = list(csv.DictReader(f))
with open(rateio_path, newline='', encoding='utf-8-sig') as f:
    rateio_rows = list(csv.DictReader(f))

def num(v):
    try:
        return round(float(v or 0), 2)
    except Exception:
        return 0.0

def as_bool(v):
    return str(v).strip().lower() in {'true','1','yes'}

COMP_BANK_ID = 12
COMP_BANK_NAME = 'COMPENSAÇÃO E RETENÇÃO'
TAX_ACCOUNT_CODES = {'4.01.001', '4.01.002', '4.01.003', '4.01.004'}
REVENUE_PREFIX = '3.'

rateio_by_row = defaultdict(list)
for r in rateio_rows:
    rr = dict(r)
    rr['allocation_amount'] = num(rr['allocation_amount'])
    rateio_by_row[int(rr['excel_row'])].append(rr)

expanded_titles = []
expanded_settlements = []
withholding_cases = []
summary = Counter()

for row in preview_rows:
    excel_row = int(row['excel_row'])
    movement_class = row['movement_class']
    allocations = rateio_by_row.get(excel_row, [])
    has_settlement = as_bool(row['has_settlement'])
    liquid_amount = num(row['gross_title_amount'])
    open_balance = num(row['open_balance_amount'])
    settlement_net = num(row['net_settlement_amount'])
    issue_date = row['movement_date'] or row['competence_date']
    due_date = row['due_date']
    competence_date = row['competence_date']
    settlement_date = row['settlement_date']
    bank_id = row['settlement_bank_account_target_id'] or ''
    bank_name = row['settlement_bank_account_target_name'] or ''

    tax_allocs = [a for a in allocations if (a.get('target_account_code') or '') in TAX_ACCOUNT_CODES]
    revenue_allocs = [a for a in allocations if (a.get('target_account_code') or '').startswith(REVENUE_PREFIX)]
    other_allocs = [a for a in allocations if a not in tax_allocs and a not in revenue_allocs]
    tax_total = round(sum(a['allocation_amount'] for a in tax_allocs), 2)
    revenue_total = round(sum(a['allocation_amount'] for a in revenue_allocs), 2)
    other_total = round(sum(a['allocation_amount'] for a in other_allocs), 2)

    is_withholding_case = (
        movement_class == 'receipt'
        and tax_total > 0
        and revenue_total > 0
        and other_total == 0
        and round(revenue_total - tax_total - liquid_amount, 2) == 0
    )

    if is_withholding_case:
        tax_label = ' / '.join(sorted({(a.get('target_account_name') or '').strip() for a in tax_allocs}))
        withholding_cases.append({
            'excel_row': excel_row,
            'descricao': row['descricao'],
            'receita_bruta': revenue_total,
            'tributo_retido': tax_total,
            'recebimento_liquido': liquid_amount,
            'tributo_label': tax_label,
            'situacao': row['situacao'],
            'settlement_date': settlement_date,
            'bank_account': bank_name,
        })

        sale_key = f'R{excel_row}-SALE'
        tax_key = f'R{excel_row}-TAX'

        # gross receivable title
        expanded_titles.append({
            'title_key': sale_key,
            'excel_row': excel_row,
            'entity_type': 'title',
            'title_kind': 'receivable',
            'scenario': 'withholding_receivable_gross',
            'descricao': row['descricao'],
            'favorecido': row['favorecido'],
            'identificador': row['identificador'],
            'issue_date': issue_date,
            'competence_date': competence_date,
            'due_date': due_date,
            'amount': revenue_total,
            'open_balance_amount': 0.0 if has_settlement else revenue_total,
            'cost_center_target_code': row['cost_center_target_code'],
            'cost_center_target_name': row['cost_center_target_name'],
            'payment_method_target_name': row['payment_method_target_name'],
            'notes': 'Título a receber bruto da venda.'
        })
        for idx, a in enumerate(revenue_allocs, start=1):
            expanded_titles.append({
                'title_key': sale_key,
                'excel_row': excel_row,
                'entity_type': 'allocation',
                'title_kind': 'receivable',
                'scenario': 'withholding_receivable_gross',
                'descricao': row['descricao'],
                'favorecido': row['favorecido'],
                'identificador': row['identificador'],
                'issue_date': issue_date,
                'competence_date': competence_date,
                'due_date': due_date,
                'amount': a['allocation_amount'],
                'open_balance_amount': '',
                'cost_center_target_code': row['cost_center_target_code'],
                'cost_center_target_name': row['cost_center_target_name'],
                'payment_method_target_name': '',
                'notes': f"Rateio receita {idx}: {a['target_account_code']} - {a['target_account_name']}"
            })

        # tax payable title
        expanded_titles.append({
            'title_key': tax_key,
            'excel_row': excel_row,
            'entity_type': 'title',
            'title_kind': 'payable',
            'scenario': 'withholding_tax_payable',
            'descricao': f"Tributo retido - {row['descricao']}",
            'favorecido': row['favorecido'],
            'identificador': row['identificador'],
            'issue_date': issue_date,
            'competence_date': competence_date,
            'due_date': due_date,
            'amount': tax_total,
            'open_balance_amount': 0.0 if has_settlement else tax_total,
            'cost_center_target_code': row['cost_center_target_code'],
            'cost_center_target_name': row['cost_center_target_name'],
            'payment_method_target_name': row['payment_method_target_name'],
            'notes': f"Título a pagar do tributo retido ({tax_label})."
        })
        for idx, a in enumerate(tax_allocs, start=1):
            expanded_titles.append({
                'title_key': tax_key,
                'excel_row': excel_row,
                'entity_type': 'allocation',
                'title_kind': 'payable',
                'scenario': 'withholding_tax_payable',
                'descricao': f"Tributo retido - {row['descricao']}",
                'favorecido': row['favorecido'],
                'identificador': row['identificador'],
                'issue_date': issue_date,
                'competence_date': competence_date,
                'due_date': due_date,
                'amount': a['allocation_amount'],
                'open_balance_amount': '',
                'cost_center_target_code': row['cost_center_target_code'],
                'cost_center_target_name': row['cost_center_target_name'],
                'payment_method_target_name': '',
                'notes': f"Rateio tributo {idx}: {a['target_account_code']} - {a['target_account_name']}"
            })

        if has_settlement:
            expanded_settlements.extend([
                {
                    'title_key': sale_key,
                    'excel_row': excel_row,
                    'component': 'bank_liquid_receipt',
                    'settlement_date': settlement_date,
                    'bank_account_target_id': bank_id,
                    'bank_account_target_name': bank_name,
                    'amount': liquid_amount,
                    'notes': 'Baixa líquida em conta bancária.'
                },
                {
                    'title_key': sale_key,
                    'excel_row': excel_row,
                    'component': 'withholding_compensation',
                    'settlement_date': settlement_date,
                    'bank_account_target_id': COMP_BANK_ID,
                    'bank_account_target_name': COMP_BANK_NAME,
                    'amount': tax_total,
                    'notes': 'Baixa do valor retido na fonte em compensações/retenções.'
                },
                {
                    'title_key': tax_key,
                    'excel_row': excel_row,
                    'component': 'withholding_compensation',
                    'settlement_date': settlement_date,
                    'bank_account_target_id': COMP_BANK_ID,
                    'bank_account_target_name': COMP_BANK_NAME,
                    'amount': tax_total,
                    'notes': 'Baixa do título a pagar do tributo retido via compensações/retenções.'
                }
            ])

        summary['withholding_cases'] += 1
    else:
        title_key = f'R{excel_row}'
        expanded_titles.append({
            'title_key': title_key,
            'excel_row': excel_row,
            'entity_type': 'title',
            'title_kind': row['title_kind'],
            'scenario': 'standard',
            'descricao': row['descricao'],
            'favorecido': row['favorecido'],
            'identificador': row['identificador'],
            'issue_date': issue_date,
            'competence_date': competence_date,
            'due_date': due_date,
            'amount': liquid_amount,
            'open_balance_amount': open_balance,
            'cost_center_target_code': row['cost_center_target_code'],
            'cost_center_target_name': row['cost_center_target_name'],
            'payment_method_target_name': row['payment_method_target_name'],
            'notes': row['notes']
        })
        for idx, a in enumerate(allocations, start=1):
            expanded_titles.append({
                'title_key': title_key,
                'excel_row': excel_row,
                'entity_type': 'allocation',
                'title_kind': row['title_kind'],
                'scenario': 'standard',
                'descricao': row['descricao'],
                'favorecido': row['favorecido'],
                'identificador': row['identificador'],
                'issue_date': issue_date,
                'competence_date': competence_date,
                'due_date': due_date,
                'amount': a['allocation_amount'],
                'open_balance_amount': '',
                'cost_center_target_code': row['cost_center_target_code'],
                'cost_center_target_name': row['cost_center_target_name'],
                'payment_method_target_name': '',
                'notes': f"Rateio {idx}: {a['target_account_code']} - {a['target_account_name']}" if a.get('target_account_code') else f"Rateio {idx}: sem conta operacional"
            })
        if has_settlement:
            expanded_settlements.append({
                'title_key': title_key,
                'excel_row': excel_row,
                'component': 'standard',
                'settlement_date': settlement_date,
                'bank_account_target_id': bank_id,
                'bank_account_target_name': bank_name,
                'amount': settlement_net,
                'notes': row['notes']
            })
        summary[f'standard_{movement_class}'] += 1

files = {
    'titles': OUT / 'save_water_financial_import_titles_expanded_v2.csv',
    'settlements': OUT / 'save_water_financial_import_settlements_expanded_v2.csv',
    'withholding': OUT / 'save_water_financial_withholding_cases_v2.csv',
    'summary': OUT / 'save_water_financial_import_expanded_summary_v2.json',
}

with open(files['titles'], 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.DictWriter(f, fieldnames=list(expanded_titles[0].keys()))
    w.writeheader(); w.writerows(expanded_titles)
with open(files['settlements'], 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.DictWriter(f, fieldnames=list(expanded_settlements[0].keys()))
    w.writeheader(); w.writerows(expanded_settlements)
with open(files['withholding'], 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.DictWriter(f, fieldnames=list(withholding_cases[0].keys()) if withholding_cases else ['excel_row'])
    w.writeheader(); w.writerows(withholding_cases)

payload = {
    'rows_original': len(preview_rows),
    'withholding_cases': len(withholding_cases),
    'expanded_title_rows': len(expanded_titles),
    'expanded_settlement_rows': len(expanded_settlements),
    'summary': dict(summary),
    'withholding_cases_sample': withholding_cases[:15],
    'files': {k: str(v) for k,v in files.items()}
}
files['summary'].write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(payload, ensure_ascii=False, indent=2))
