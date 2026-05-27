from app import create_app
from models import db
from models.financial import FinancialSchedule
from services.financial_schedule_service import FinancialScheduleService
import json

BATCH='conta_azul_save_water_canonical_schedule_20260525_v1'
app = create_app('production')
with app.app_context():
    schedules = FinancialSchedule.query.filter(FinancialSchedule.company_id==1, FinancialSchedule.deleted_at.is_(None)).order_by(FinancialSchedule.id.asc()).all()
    schedules = [s for s in schedules if (s.metadata_json or {}).get('migration_schedule_batch_id') == BATCH]
    samples = []
    for source_code in ['CA-SW-R181', 'CA-SW-R3-SALE', 'CA-SW-R227']:
        found = next((s for s in schedules if (s.metadata_json or {}).get('source_entry_code') == source_code), None)
        if found:
            detail = FinancialScheduleService.get_schedule_detail(schedule_id=found.id, company_id=1, allowed_company_ids=[1])[0]
            samples.append({
                'source_entry_code': source_code,
                'schedule_id': found.id,
                'schedule_code': found.schedule_code,
                'description': found.description,
                'status': found.status,
                'summary': detail.get('summary'),
                'allocations': detail.get('allocations'),
            })
    print(json.dumps({'count': len(schedules), 'samples': samples}, ensure_ascii=False, indent=2, default=str))
