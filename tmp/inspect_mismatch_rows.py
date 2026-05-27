import csv, json
from collections import defaultdict
from pathlib import Path

OUT=Path(r'C:\GestaoVersus\app32\outputs')
with open(OUT/'save_water_financial_import_preview.csv', newline='', encoding='utf-8-sig') as f:
    preview=list(csv.DictReader(f))
with open(OUT/'save_water_financial_import_rateio.csv', newline='', encoding='utf-8-sig') as f:
    rateio=list(csv.DictReader(f))
with open(OUT/'save_water_financial_validation_issues.csv', newline='', encoding='utf-8-sig') as f:
    issues=list(csv.DictReader(f))
rateio_by_row=defaultdict(list)
for r in rateio:
    rateio_by_row[int(r['excel_row'])].append(r)
preview_by_row={int(r['excel_row']):r for r in preview}
rows=[]
for it in issues:
    rownum=int(it['excel_row'])
    if it['issue']!='rateio_title_mismatch':
        continue
    row=preview_by_row[rownum]
    rows.append({
        'excel_row': rownum,
        'descricao': row['descricao'],
        'gross_title_amount': row['gross_title_amount'],
        'net_settlement_amount': row['net_settlement_amount'],
        'situacao': row['situacao'],
        'rateio': rateio_by_row[rownum],
    })
print(json.dumps(rows[:20], ensure_ascii=False, indent=2))
