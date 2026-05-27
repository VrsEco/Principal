from pathlib import Path
p=Path(r'/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/www/app32/app32/services/financial_schedule_service.py')
lines=p.read_text(encoding='utf-8').splitlines()
for i in range(205,213):
    print(str(i+1)+': '+lines[i])
