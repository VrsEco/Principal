import json
from pathlib import Path
p=Path(r'C:\GestaoVersus\app32\tmp\aux_prepare_result.json')
data=None
for enc in ('utf-8','utf-8-sig','cp1252','latin-1'):
    try:
        data=json.loads(p.read_text(encoding=enc))
        break
    except Exception:
        pass
print('SUMMARY', data['summary'])
print('UNMAPPED')
print(json.dumps(data['unmapped_categories'], ensure_ascii=False, indent=2))
print('FIRST_10_MISSING')
print(json.dumps(data['missing_counterparties'][:10], ensure_ascii=False, indent=2))
