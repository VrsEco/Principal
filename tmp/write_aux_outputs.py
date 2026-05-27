import json, csv
from pathlib import Path
raw=Path(r'C:\GestaoVersus\app32\tmp\aux_prepare_result.json').read_bytes()
for enc in ('utf-8','utf-8-sig','cp1252','latin-1'):
    try:
        data=json.loads(raw.decode(enc)); break
    except Exception: pass
outdir=Path(r'C:\GestaoVersus\app32\outputs')
outdir.mkdir(exist_ok=True)
with open(outdir/'save_water_missing_counterparties.csv','w',newline='',encoding='utf-8-sig') as f:
    w=csv.DictWriter(f, fieldnames=['name','document_number','count'])
    w.writeheader(); w.writerows(data['missing_counterparties'])
with open(outdir/'save_water_category_map.csv','w',newline='',encoding='utf-8-sig') as f:
    w=csv.writer(f)
    w.writerow(['source_text','source_code','source_name','target_id','target_code','target_name','reason'])
    for item in data['category_map']:
        s=item['source']; t=item['target']
        w.writerow([s['source_text'],s['source_code'],s['source_name'],t['id'],t['code'],t['name'],item['reason']])
with open(outdir/'save_water_unmapped_categories.csv','w',newline='',encoding='utf-8-sig') as f:
    w=csv.writer(f)
    w.writerow(['source_text','source_code','source_name','reason'])
    for item in data['unmapped_categories']:
        s=item['source']
        w.writerow([s['source_text'],s['source_code'],s['source_name'],item['reason']])
print('OK')
print(outdir/'save_water_missing_counterparties.csv')
print(outdir/'save_water_category_map.csv')
print(outdir/'save_water_unmapped_categories.csv')
