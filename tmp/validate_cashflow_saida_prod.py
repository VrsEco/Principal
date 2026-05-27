from __future__ import annotations
import json, os, sys

VENV_SITE = '/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/.virtualenv/3.12/lib/python3.12/site-packages'
APP_DIR = '/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/www/app32'
if VENV_SITE not in sys.path:
    sys.path.insert(0, VENV_SITE)
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)
os.environ.setdefault('FLASK_ENV', 'production')
os.environ.setdefault('FLASK_CONFIG', 'production')
os.environ.setdefault('OPENAI_API_KEY', 'dummy')
os.environ['APP_BOOTSTRAP_DB_SCHEMA'] = '0'
os.environ['APP_BOOTSTRAP_RUNTIME_SERVICES'] = '0'
try:
    from dotenv import load_dotenv
    load_dotenv(f'{APP_DIR}/.env')
except Exception:
    pass

from sqlalchemy import text
from app import create_app
from models import db
from services.financial_report_service import FinancialReportService

bank_ids = [7,8,10,11,12,13,14,15]
filters = {
    'enable_title_exclusions': 'false',
    'bank_account_ids': [str(i) for i in bank_ids],
    'period_start': '2026-06-01',
    'period_end': '2026-06-30',
    'frequency': 'weekly',
    'projected_values_mode': 'without_financial_correction',
}
app = create_app('production')
with app.app_context():
    bank_rows = db.session.execute(text('''
        SELECT id, company_id, name
        FROM financial_bank_accounts
        WHERE id = ANY(:ids)
        ORDER BY id
    '''), {'ids': bank_ids}).mappings().all()
    companies = sorted({int(r['company_id']) for r in bank_rows if r['company_id'] is not None})
    company_id = companies[0] if len(companies) == 1 else None
    result = {'bank_accounts': [dict(r) for r in bank_rows], 'companies': companies, 'company_id': company_id}
    if company_id:
        report, error = FinancialReportService.build_management_report(
            company_id=company_id,
            report_type='fluxo-caixa',
            filters=filters,
            allowed_company_ids=[company_id],
        )
        result['error'] = error
        if report:
            result['columns'] = report.get('columns')
            result['rows_saida'] = [
                {
                    'periodo': row.get('periodo'),
                    'entrada': row.get('entrada'),
                    'saida': row.get('saida'),
                    'saldo_final': row.get('saldo_final'),
                }
                for row in (report.get('rows') or [])
            ]
            result['summary_saida'] = [c for c in (report.get('summary_cards') or []) if 'Saídas' in str(c.get('label'))]
            result['selected_payables_totals'] = report.get('selected_payables_totals')
            result['selected_receivables_totals'] = report.get('selected_receivables_totals')
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
