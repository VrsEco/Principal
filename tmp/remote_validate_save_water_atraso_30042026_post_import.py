from __future__ import annotations
import json
from app import create_app
from models.financial import FinancialSchedule
from services.financial_title_balance_service import FinancialTitleBalanceService

COMPANY_ID = 1
BATCH_ID = 'conta_azul_save_water_canonical_schedule_atraso_30042026_v1'

app = create_app('production')
with app.app_context():
    schedules = FinancialSchedule.query.filter(FinancialSchedule.company_id==COMPANY_ID, FinancialSchedule.deleted_at.is_(None)).all()
    targets = [s for s in schedules if (s.metadata_json or {}).get('migration_schedule_batch_id') == BATCH_ID]
    counts = {'payable':0,'receivable':0,'active':0,'completed':0}
    total = 0.0
    open_total = 0.0
    sample = []
    for s in targets:
        counts[s.entry_type] = counts.get(s.entry_type,0)+1
        counts[s.status] = counts.get(s.status,0)+1
        bal = FinancialTitleBalanceService.calculate_for_schedule(schedule=s) or {}
        total += float(bal.get('principal_amount') or 0)
        open_total += float(bal.get('principal_open') or 0)
        if len(sample) < 5:
            sample.append({
                'schedule_id': s.id,
                'description': s.description,
                'entry_type': s.entry_type,
                'status': s.status,
                'principal_amount': bal.get('principal_amount'),
                'principal_open': bal.get('principal_open'),
            })
    print(json.dumps({
        'batch_id': BATCH_ID,
        'schedule_count': len(targets),
        'counts': counts,
        'principal_total': round(total,2),
        'principal_open_total': round(open_total,2),
        'sample': sample,
    }, ensure_ascii=False, indent=2))
