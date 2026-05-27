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

def norm(v):
    v = '' if v is None else str(v).strip()
    v = unicodedata.normalize('NFKD', v).encode('ascii', 'ignore').decode('ascii').lower()
    v = re.sub(r'\s+', ' ', v)
    return v.strip()

def num(v):
    try:
        return round(float(v or 0), 2)
    except Exception:
        return 0.0

def as_bool(v):
    return str(v).strip().lower() in {'true','1','yes'}

COMP_BANK_ID = 12
COMP_BANK_NAME = 'COMPENSAÇÃO E RETENÇÃO'
ISS_CODES = {'4.01.002', '4.01.004'}  # ISS Retido NF / ISS Sobre Vendas no plano Versus

rateio_by_row = defaultdict(list)
for r in rateio_rows:
    rr = dict(r)
    rr['allocation_amount'] = num(rr['allocation_amount'])
    rateio_by_row[int(rr['excel_row'])].append(rr)

expanded_titles = []
expanded_settlements = []
retention_cases = []
summary = Counter()

for row in preview_rows:
    excel_row = int(row['excel_row'])
    movement_class = row['movement_class']
    allocations = rateio_by_row.get(excel_row, [])
    has_settlement = as_bool(row['has_settlement'])
    gross = num(row['gross_title_amount'])
    net = num(row['net_settlement_amount'])
    open_balance = num(row['open_balance_amount'])
    issue_date = row['movement_date'] or row['competence_date']
    due_date = row['due_date']
    competence_date = row['competence_date']
    settlement_date = row['settlement_date']
    bank_id = row['settlement_bank_account_target_id'] or ''
    bank_name = row['settlement_bank_account_target_name'] or ''

    iss_allocs = [a for a in allocations if (a.get('target_account_code') or '') in ISS_CODES]
    non_iss_allocs = [a for a in allocations if a not in iss_allocs]
    iss_total = round(sum(a['allocation_amount'] for a in iss_allocs), 2)
    non_iss_total = round(sum(a['allocation_amount'] for a in non_iss_allocs), 2)

    is_retention_case = (
        movement_class == 'receipt' and iss_total > 0 and round(non_iss_total - gross, 2) == 0
    )

    if is_retention_case:
        retention_cases.append({
            'excel_row': excel_row,
            'descricao': row['descricao'],
            'gross_receivable': non_iss_total,
            'iss_withheld': iss_total,
            'liquid_received': gross,
            'settlement_date': settlement_date,
            'bank_account': bank_name,
        })

        # Title 1: sale receivable gross
        title_sale_id = f'R{excel_row}-SALE'
        expanded_titles.append({
            'title_key': title_sale_id,
            'excel_row': excel_row,
            'title_kind': 'receivable',
            'scenario': 'receipt_with_iss_withholding_sale',
            'descricao': row['descricao'],
            'favorecido': row['favorecido'],
            'identificador': row['identificador'],
            'issue_date': issue_date,
            'competence_date': competence_date,
            'due_date': due_date,
            'gross_amount': round(non_iss_total, 2),
            'open_balance_amount': 0.0 if has_settlement else round(non_iss_total, 2),
            'payment_method_target_id': row['payment_method_target_id'],
            'payment_method_target_name': row['payment_method_target_name'],
            'cost_center_target_id': row['cost_center_target_id'],
            'cost_center_target_code': row['cost_center_target_code'],
            'cost_center_target_name': row['cost_center_target_name'],
            'title_notes': 'Título bruto da venda; retenção tratada como componente de baixa e obrigação fiscal apartada.'
        })
        for idx, a in enumerate(non_iss_allocs, start=1):
            expanded_titles.append({
                'title_key': title_sale_id,
                'excel_row': excel_row,
                'title_kind': 'receivable_allocation',
                'scenario': 'receipt_with_iss_withholding_sale',
                'descricao': row['descricao'],
                'favorecido': row['favorecido'],
                'identificador': row['identificador'],
                'issue_date': issue_date,
                'competence_date': competence_date,
                'due_date': due_date,
                'gross_amount': a['allocation_amount'],
                'open_balance_amount': '',
                'payment_method_target_id': '',
                'payment_method_target_name': '',
                'cost_center_target_id': row['cost_center_target_id'],
                'cost_center_target_code': row['cost_center_target_code'],
                'cost_center_target_name': row['cost_center_target_name'],
                'title_notes': f"Rateio {idx}: {a['target_account_code']} - {a['target_account_name']}"
            })
        # settlement for sale title: bank liquid + comp withholding
        if has_settlement:
            expanded_settlements.append({
                'title_key': title_sale_id,
                'excel_row': excel_row,
                'settlement_component': 'bank',
                'settlement_date': settlement_date,
                'bank_account_target_id': bank_id,
                'bank_account_target_name': bank_name,
                'amount': round(gross, 2),
                'interest_amount': num(row['interest_amount']),
                'penalty_amount': num(row['penalty_amount']),
                'discount_amount': num(row['discount_amount']),
                'fee_amount': num(row['fee_amount']),
                'notes': 'Recebimento líquido em conta bancária.'
            })
            expanded_settlements.append({
                'title_key': title_sale_id,
                'excel_row': excel_row,
                'settlement_component': 'withholding_compensation',
                'settlement_date': settlement_date,
                'bank_account_target_id': COMP_BANK_ID,
                'bank_account_target_name': COMP_BANK_NAME,
                'amount': round(iss_total, 2),
                'interest_amount': 0.0,
                'penalty_amount': 0.0,
                'discount_amount': 0.0,
                'fee_amount': 0.0,
                'notes': 'Componente de baixa por imposto retido na fonte.'
            })

        # Title 2: ISS retained payable
        title_iss_id = f'R{excel_row}-ISS'
        expanded_titles.append({
            'title_key': title_iss_id,
            'excel_row': excel_row,
            'title_kind': 'payable',
            'scenario': 'receipt_with_iss_withholding_tax',
            'descricao': f"ISS Retido - {row['descricao']}",
            'favorecido': row['favorecido'],
            'identificador': row['identificador'],
            'issue_date': issue_date,
            'competence_date': competence_date,
            'due_date': due_date,
            'gross_amount': round(iss_total, 2),
            'open_balance_amount': 0.0 if has_settlement else round(iss_total, 2),
            'payment_method_target_id': row['payment_method_target_id'],
            'payment_method_target_name': row['payment_method_target_name'],
            'cost_center_target_id': row['cost_center_target_id'],
            'cost_center_target_code': row['cost_center_target_code'],
            'cost_center_target_name': row['cost_center_target_name'],
            'title_notes': 'Obrigação fiscal gerada pelo ISS retido na fonte.'
        })
        for idx, a in enumerate(iss_allocs, start=1):
            expanded_titles.append({
                'title_key': title_iss_id,
                'excel_row': excel_row,
                'title_kind': 'payable_allocation',
                'scenario': 'receipt_with_iss_withholding_tax',
                'descricao': f"ISS Retido - {row['descricao']}",
                'favorecido': row['favorecido'],
                'identificador': row['identificador'],
                'issue_date': issue_date,
                'competence_date': competence_date,
                'due_date': due_date,
                'gross_amount': a['allocation_amount'],
                'open_balance_amount': '',
                'payment_method_target_id': '',
                'payment_method_target_name': '',
                'cost_center_target_id': row['cost_center_target_id'],
                'cost_center_target_code': row['cost_center_target_code'],
                'cost_center_target_name': row['cost_center_target_name'],
                'title_notes': f"Rateio ISS {idx}: {a['target_account_code']} - {a['target_account_name']}"
            })
        if has_settlement:
            expanded_settlements.append({
                'title_key': title_iss_id,
                'excel_row': excel_row,
                'settlement_component': 'withholding_compensation',
                'settlement_date': settlement_date,
                'bank_account_target_id': COMP_BANK_ID,
                'bank_account_target_name': COMP_BANK_NAME,
                'amount': round(iss_total, 2),
                'interest_amount': 0.0,
                'penalty_amount': 0.0,
                'discount_amount': 0.0,
                'fee_amount': 0.0,
                'notes': 'Baixa do título fiscal via compensação/retenção na data do recebimento.'
            })
        summary['titles_receipt_withholding_sale'] += 1
        summary['titles_receipt_withholding_tax'] += 1
    else:
        title_id = f'R{excel_row}'
        expanded_titles.append({
            'title_key': title_id,
            'excel_row': excel_row,
            'title_kind': row['title_kind'],
            'scenario': 'standard',
            'descricao': row['descricao'],
            'favorecido': row['favorecido'],
            'identificador': row['identificador'],
            'issue_date': issue_date,
            'competence_date': competence_date,
            'due_date': due_date,
            'gross_amount': gross,
            'open_balance_amount': open_balance,
            'payment_method_target_id': row['payment_method_target_id'],
            'payment_method_target_name': row['payment_method_target_name'],
            'cost_center_target_id': row['cost_center_target_id'],
            'cost_center_target_code': row['cost_center_target_code'],
            'cost_center_target_name': row['cost_center_target_name'],
            'title_notes': row['notes'],
        })
        for idx, a in enumerate(allocations, start=1):
            expanded_titles.append({
                'title_key': title_id,
                'excel_row': excel_row,
                'title_kind': f"{row['title_kind']}_allocation",
                'scenario': 'standard',
                'descricao': row['descricao'],
                'favorecido': row['favorecido'],
                'identificador': row['identificador'],
                'issue_date': issue_date,
                'competence_date': competence_date,
                'due_date': due_date,
                'gross_amount': a['allocation_amount'],
                'open_balance_amount': '',
                'payment_method_target_id': '',
                'payment_method_target_name': '',
                'cost_center_target_id': row['cost_center_target_id'],
                'cost_center_target_code': row['cost_center_target_code'],
                'cost_center_target_name': row['cost_center_target_name'],
                'title_notes': f"Rateio {idx}: {a['target_account_code']} - {a['target_account_name']}" if a.get('target_account_code') else f"Rateio {idx}: sem conta operacional (transferência/compensação)",
            })
        if has_settlement:
            expanded_settlements.append({
                'title_key': title_id,
                'excel_row': excel_row,
                'settlement_component': 'standard',
                'settlement_date': settlement_date,
                'bank_account_target_id': bank_id,
                'bank_account_target_name': bank_name,
                'amount': net,
                'interest_amount': num(row['interest_amount']),
                'penalty_amount': num(row['penalty_amount']),
                'discount_amount': num(row['discount_amount']),
                'fee_amount': num(row['fee_amount']),
                'notes': row['notes'],
            })
        summary[f'standard_{movement_class}'] += 1

expanded_titles_csv = OUT / 'save_water_financial_import_titles_expanded.csv'
expanded_settlements_csv = OUT / 'save_water_financial_import_settlements_expanded.csv'
retention_cases_csv = OUT / 'save_water_financial_retention_cases.csv'
summary_json = OUT / 'save_water_financial_import_expanded_summary.json'

with open(expanded_titles_csv, 'w', newline='', encoding='utf-8-sig') as f:
    writer = csv.DictWriter(f, fieldnames=list(expanded_titles[0].keys()))
    writer.writeheader(); writer.writerows(expanded_titles)
with open(expanded_settlements_csv, 'w', newline='', encoding='utf-8-sig') as f:
    writer = csv.DictWriter(f, fieldnames=list(expanded_settlements[0].keys()))
    writer.writeheader(); writer.writerows(expanded_settlements)
with open(retention_cases_csv, 'w', newline='', encoding='utf-8-sig') as f:
    writer = csv.DictWriter(f, fieldnames=list(retention_cases[0].keys()) if retention_cases else ['excel_row'])
    writer.writeheader(); writer.writerows(retention_cases)

payload = {
    'rows_original': len(preview_rows),
    'retention_cases': len(retention_cases),
    'expanded_title_rows': len(expanded_titles),
    'expanded_settlement_rows': len(expanded_settlements),
    'summary': dict(summary),
    'retention_cases_sample': retention_cases[:15],
    'files': {
        'titles_expanded_csv': str(expanded_titles_csv),
        'settlements_expanded_csv': str(expanded_settlements_csv),
        'retention_cases_csv': str(retention_cases_csv),
    }
}
summary_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(payload, ensure_ascii=False, indent=2))
