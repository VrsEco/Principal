from pathlib import Path
import re

from flask import Flask, session

from api.routes import work_journey as work_journey_route
from api.routes import work_journey_agendas as work_journey_agendas_route
from api.routes import work_journey_report as work_journey_report_route
from utils import permissions


def _app():
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.secret_key = 'test'
    return app


def test_work_journey_routes_reject_foreign_company_before_any_service(monkeypatch):
    app = _app()
    monkeypatch.setattr(permissions, 'has_permission', lambda *_args: True)

    guarded_routes = (
        work_journey_route.api_get_work_journey_board,
        work_journey_agendas_route.api_get_agenda,
        work_journey_report_route.work_journey_report_page,
    )
    with app.test_request_context('/api/companies/22/work-journey'):
        session['active_company_id'] = 9
        for protected in guarded_routes:
            payload, status = protected(22)
            assert status == 403
            assert 'não corresponde' in payload['error']


def test_work_journey_company_url_routes_bind_to_active_tenant_guard():
    root = Path(__file__).resolve().parents[1] / 'api' / 'routes'
    for filename in (
        'work_journey.py',
        'work_journey_agendas.py',
        'work_journey_report.py',
    ):
        source = (root / filename).read_text(encoding='utf-8')
        company_route_blocks = re.findall(
            r"@\w+_bp\.route\([^\n]*<int:company_id>[^\n]*\)([\s\S]{0,160}?)def\s+\w+",
            source,
        )
        assert company_route_blocks
        assert all('@active_company_permission_required' in block for block in company_route_blocks)


def test_work_journey_url_routes_do_not_switch_active_tenant_from_company_id():
    root = Path(__file__).resolve().parents[1] / 'api' / 'routes'
    journey_source = (root / 'work_journey.py').read_text(encoding='utf-8')
    report_source = (root / 'work_journey_report.py').read_text(encoding='utf-8')
    assert "def work_journey_page(company_id: int):\n    session['active_company_id'] = company_id" not in journey_source
    assert "def _build_report_payload(company_id: int) -> tuple[object, dict, bool]:\n    session['active_company_id'] = company_id" not in report_source
