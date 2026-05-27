from app import create_app
from models.financial import FinancialSchedule
from services.financial_title_balance_service import FinancialTitleBalanceService
import json
BATCH='conta_azul_save_water_canonical_schedule_20260525_v1'
app = create_app('production')
with app.app_context():
    schedules = FinancialSchedule.query.filter(FinancialSchedule.company_id==1, FinancialSchedule.deleted_at.is_(None)).all()
    schedules = [s for s in schedules if (s.metadata_json or {}).get('migration_schedule_batch_id') == BATCH]
    out=[]
    for source_code in ['CA-SW-R3-SALE','CA-SW-R227']:
        s=next((x for x in schedules if (x.metadata_json or {}).get('source_entry_code')==source_code), None)
        if s:
            bal=FinancialTitleBalanceService.calculate_for_schedule(schedule=s)
            out.append({'source_entry_code':source_code,'schedule_id':s.id,'principal_amount':bal.get('principal_amount'),'principal_settled':bal.get('principal_settled'),'principal_open':bal.get('principal_open'),'total_open':bal.get('total_open'),'settlement_count':bal.get('settlement_count'),'entry_count':bal.get('entry_count'),'settlement_state':bal.get('settlement_state'),'operational_state':bal.get('operational_state')})
    print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
