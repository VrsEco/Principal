from __future__ import annotations
import json
from app import create_app
from models.financial import FinancialSchedule
from services.financial_schedule_service import FinancialScheduleService
from services.financial_title_balance_service import FinancialTitleBalanceService

COMPANY_ID = 1
ENTRY_CODES = [
    'CA-SW2-R2',
    'CA-SW2-R15',
    'CA-SW2-R13-SALE',
    'CA-SW2-R13-TAX',
    'CA-SW2-R66',
]

app = create_app('production')
with app.app_context():
    out = []
    for code in ENTRY_CODES:
        schedule = None
        for row in FinancialSchedule.query.filter(FinancialSchedule.company_id==COMPANY_ID, FinancialSchedule.deleted_at.is_(None)).all():
            if (row.metadata_json or {}).get('source_entry_code') == code:
                schedule = row
                break
        if not schedule:
            out.append({'entry_code': code, 'found': False})
            continue
        detail, err = FinancialScheduleService.get_schedule_detail(schedule_id=schedule.id, company_id=COMPANY_ID, allowed_company_ids=[COMPANY_ID])
        bal = FinancialTitleBalanceService.calculate_for_schedule(schedule=schedule) or {}
        out.append({
            'entry_code': code,
            'found': True,
            'schedule_id': schedule.id,
            'schedule_code': schedule.schedule_code,
            'description': schedule.description,
            'entry_type': schedule.entry_type,
            'status': schedule.status,
            'counterparty_name': (detail.get('counterparty') or {}).get('name'),
            'template_amount': detail.get('template_amount'),
            'summary_principal_amount': (detail.get('summary') or {}).get('principal_amount'),
            'summary_principal_open': (detail.get('summary') or {}).get('principal_open'),
            'balance_principal_amount': bal.get('principal_amount'),
            'balance_principal_open': bal.get('principal_open'),
            'allocations': detail.get('allocations') or [],
        })
    print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
