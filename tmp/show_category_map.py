import json
from pathlib import Path
raw=Path(r'C:\GestaoVersus\app32\tmp\aux_prepare_result.json').read_bytes()
for enc in ('utf-8','utf-8-sig','cp1252','latin-1'):
    try:
        data=json.loads(raw.decode(enc)); break
    except Exception: pass
print('UNMAPPED_CATEGORIES')
for item in data['unmapped_categories']:
    s=item['source']
    print(f"- {s['source_text']} ({item['reason']})")
print('\nFIRST_20_CATEGORY_MAP')
for item in data['category_map'][:20]:
    s=item['source']; t=item['target']
    print(f"- {s['source_text']} => {t['code']} - {t['name']} [{item['reason']}]")
