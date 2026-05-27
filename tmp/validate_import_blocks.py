import csv, json
from collections import Counter, defaultdict
from pathlib import Path

BASE = Path(r'C:\GestaoVersus\app32\outputs')
preview_path = BASE / 'save_water_financial_import_preview.csv'
rateio_path = BASE / 'save_water_financial_import_rateio.csv'

with open(preview_path, newline='', encoding='utf-8-sig') as f:
    preview = list(csv.DictReader(f))
with open(rateio_path, newline='', encoding='utf-8-sig') as f:
    rateio = list(csv.DictReader(f))

rateio_by_row = defaultdict(list)
for r in rateio:
    rateio_by_row[int(r['excel_row'])].append(r)

def num(v):
    try:
        return round(float(v or 0), 2)
    except Exception:
        return 0.0

def is_true(v):
    return str(v).strip().lower() in {'true', '1', 'yes'}

open_rows = []
settled_rows = []
transfer_rows = []
issues = []
summary = Counter()
issue_breakdown = Counter()

for row in preview:
    excel_row = int(row['excel_row'])
    movement_class = row['movement_class']
    gross = num(row['gross_title_amount'])
    open_balance = num(row['open_balance_amount'])
    settlement = num(row['net_settlement_amount'])
    principal_settlement = num(row['principal_settlement_amount'])
    juros = num(row['interest_amount'])
    multa = num(row['penalty_amount'])
    desconto = num(row['discount_amount'])
    taxas = num(row['fee_amount'])
    has_settlement = is_true(row['has_settlement'])
    allocations = rateio_by_row.get(excel_row, [])
    rateio_total = round(sum(num(a['allocation_amount']) for a in allocations), 2)
    mapped_alloc_total = round(sum(num(a['allocation_amount']) for a in allocations if a['target_account_id']), 2)

    block = 'open' if not has_settlement and movement_class not in {'transfer','compensation'} else 'settled' if movement_class not in {'transfer','compensation'} else 'transfer'
    summary[f'block_{block}'] += 1

    record = {
        'excel_row': excel_row,
        'descricao': row['descricao'],
        'movement_class': movement_class,
        'situacao': row['situacao'],
        'gross_title_amount': gross,
        'rateio_total': rateio_total,
        'mapped_rateio_total': mapped_alloc_total,
        'open_balance_amount': open_balance,
        'net_settlement_amount': settlement,
        'principal_settlement_amount': principal_settlement,
        'interest_amount': juros,
        'penalty_amount': multa,
        'discount_amount': desconto,
        'fee_amount': taxas,
        'settlement_bank_account_target_name': row['settlement_bank_account_target_name'],
    }

    if block == 'open':
        open_rows.append(record)
        if open_balance <= 0:
            issues.append({**record, 'issue': 'open_without_open_balance'})
            issue_breakdown['open_without_open_balance'] += 1
        if has_settlement:
            issues.append({**record, 'issue': 'open_with_settlement'})
            issue_breakdown['open_with_settlement'] += 1
    elif block == 'settled':
        settled_rows.append(record)
        if settlement <= 0:
            issues.append({**record, 'issue': 'settled_without_settlement_value'})
            issue_breakdown['settled_without_settlement_value'] += 1
        if not row['settlement_bank_account_target_name']:
            issues.append({**record, 'issue': 'settled_without_bank_account'})
            issue_breakdown['settled_without_bank_account'] += 1
        if open_balance != 0:
            issues.append({**record, 'issue': 'settled_with_open_balance'})
            issue_breakdown['settled_with_open_balance'] += 1
    else:
        transfer_rows.append(record)
        if mapped_alloc_total > 0:
            issues.append({**record, 'issue': 'transfer_with_operational_rateio'})
            issue_breakdown['transfer_with_operational_rateio'] += 1

    # generic validations
    if not allocations:
        issues.append({**record, 'issue': 'missing_rateio'})
        issue_breakdown['missing_rateio'] += 1

    # rateio tolerance: settled rows may diverge from title because taxes/retentions may be split into extra categories.
    diff = round(rateio_total - gross, 2)
    if movement_class in {'payment','receipt'} and abs(diff) > 0.05:
        # if diff is approximately taxes+juros+multa-desconto treat as explainable, else flag
        explainable = round(abs(diff) - abs((juros + multa + taxas - desconto)), 2)
        if explainable > 0.05:
            issues.append({**record, 'issue': 'rateio_title_mismatch', 'difference': diff})
            issue_breakdown['rateio_title_mismatch'] += 1

result = {
    'summary': {
        'open_titles': len(open_rows),
        'settled_titles': len(settled_rows),
        'transfer_titles': len(transfer_rows),
        'issues_total': len(issues),
        'issue_breakdown': dict(issue_breakdown),
    },
    'open_sample': open_rows[:10],
    'settled_sample': settled_rows[:10],
    'transfer_sample': transfer_rows[:10],
    'issues_sample': issues[:30],
}

(Path(r'C:\GestaoVersus\app32\outputs') / 'save_water_financial_validation_summary.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
with open(Path(r'C:\GestaoVersus\app32\outputs') / 'save_water_financial_validation_issues.csv', 'w', newline='', encoding='utf-8-sig') as f:
    if issues:
        fieldnames = sorted({k for row in issues for k in row.keys()})
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader(); w.writerows(issues)
print(json.dumps(result, ensure_ascii=False, indent=2))
