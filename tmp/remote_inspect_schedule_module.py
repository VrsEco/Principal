from app import create_app
import services.financial_schedule_service as mod
from models.financial import FinancialSchedule
import json
app=create_app('production')
with app.app_context():
    s=FinancialSchedule.query.filter(FinancialSchedule.id==722, FinancialSchedule.company_id==1, FinancialSchedule.deleted_at.is_(None)).first()
    detail, err = mod.FinancialScheduleService.get_schedule_detail(schedule_id=722, company_id=1, allowed_company_ids=[1])
    print(json.dumps({'module_file': mod.__file__, 'has_summary': 'summary' in (detail or {}), 'summary': (detail or {}).get('summary'), 'err': err}, ensure_ascii=False, indent=2, default=str))
