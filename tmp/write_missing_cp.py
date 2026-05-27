import json
from pathlib import Path
p=Path(r'C:\GestaoVersus\app32\tmp\aux_prepare_result.json')
raw=p.read_bytes()
text=None
for enc in ('utf-8','utf-8-sig','cp1252','latin-1'):
    try:
        text=raw.decode(enc)
        data=json.loads(text)
        break
    except Exception:
        continue
missing=data['missing_counterparties']
Path(r'C:\GestaoVersus\app32\tmp\missing_counterparties.json').write_text(json.dumps(missing, ensure_ascii=False, indent=2), encoding='utf-8')
print(len(missing))
print(json.dumps(missing[:5], ensure_ascii=False, indent=2))
