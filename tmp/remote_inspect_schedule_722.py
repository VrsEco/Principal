from app import create_app
from models.financial import FinancialSchedule
from services.financial_schedule_service import FinancialScheduleService
from services.financial_title_balance_service import FinancialTitleBalanceService
import json

SCHEDULE_ID = 722
app = create_app('production')
with app.app_context():
    schedule = FinancialSchedule.query.filter(FinancialSchedule.id == SCHEDULE_ID, FinancialSchedule.company_id == 1, FinancialSchedule.deleted_at.is_(None)).first()
    if not schedule:
        print(json.dumps({'ok': False, 'error': 'schedule_not_found'}))
    else:
        detail, err = FinancialScheduleService.get_schedule_detail(schedule_id=SCHEDULE_ID, company_id=1, allowed_company_ids=[1])
        balance = FinancialTitleBalanceService.calculate_for_schedule(schedule=schedule)
        print(json.dumps({
            'ok': True,
            'schedule_id': SCHEDULE_ID,
            'schedule_code': schedule.schedule_code,
            'description': schedule.description,
            'status': schedule.status,
            'detail_summary': detail.get('summary') if detail else None,
            'detail_summary_error': err,
            'balance': balance,
            'metadata_json': schedule.metadata_json,
        }, ensure_ascii=False, indent=2, default=str))
