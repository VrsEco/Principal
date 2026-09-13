from flask import Flask, session
from pathlib import Path

from api.resources import indicator as indicator_resource
from api.resources import okr as okr_resource
from api.resources import plan as plan_resource
from utils import permissions


def _app():
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.secret_key = 'test'
    return app


def test_active_company_permission_rejects_request_tenant_mismatch(monkeypatch):
    app = _app()
    checked_companies = []
    monkeypatch.setattr(
        permissions,
        'has_permission',
        lambda company_id, resource, action: checked_companies.append(company_id) or True,
    )

    @permissions.active_company_permission_required('okrs', 'view')
    def protected():
        return {'ok': True}, 200

    with app.test_request_context('/api/okrs-global?company_id=22'):
        session['active_company_id'] = 9
        payload, status = protected()

    assert status == 403
    assert 'não corresponde' in payload['error']
    assert checked_companies == []


def test_active_company_permission_uses_session_company(monkeypatch):
    app = _app()
    checked_companies = []
    monkeypatch.setattr(
        permissions,
        'has_permission',
        lambda company_id, resource, action: checked_companies.append(company_id) or True,
    )

    @permissions.active_company_permission_required('plans', 'edit')
    def protected():
        return {'ok': True}, 200

    with app.test_request_context('/api/plans?company_id=9'):
        session['active_company_id'] = 9
        payload, status = protected()

    assert status == 200
    assert payload == {'ok': True}
    assert checked_companies == [9]


def test_strategy_resources_prefer_active_company_over_client_value():
    app = _app()
    with app.test_request_context('/api/indicators?company_id=22'):
        session['active_company_id'] = 9
        assert indicator_resource.get_request_company_id() == 9
        assert okr_resource._get_request_company_id() == 9
        assert plan_resource._get_request_company_id() == 9


def test_indicator_batch_cannot_choose_company_per_entry():
    source = (
        Path(__file__).resolve().parents[1] / 'api' / 'resources' / 'indicator.py'
    ).read_text(encoding='utf-8')

    assert "entry['company_id'] = company_id" in source
    assert "if 'company_id' not in entry:" not in source
from pathlib import Path

from api.resources import process as process_resource
from api.resources import project as project_resource


def test_project_and_process_resources_prefer_active_company_over_client_value():
    app = _app()
    with app.test_request_context('/api/projects?company_id=22'):
        session['active_company_id'] = 9
        assert project_resource.get_request_company_id() == 9
    with app.test_request_context('/api/processes?company_id=22'):
        session['active_company_id'] = 9
        assert process_resource.get_request_company_id() == 9


def test_active_company_permission_rejects_route_tenant_mismatch(monkeypatch):
    app = _app()
    monkeypatch.setattr(permissions, 'has_permission', lambda *args: True)

    @permissions.active_company_permission_required('processes', 'view')
    def protected(company_id=None):
        return {'ok': True}, 200

    with app.test_request_context('/api/companies/22/processes'):
        session['active_company_id'] = 9
        payload, status = protected(company_id=22)

    assert status == 403
    assert 'não corresponde' in payload['error']


def test_project_and_process_api_resources_use_active_company_guard():
    root = Path(__file__).resolve().parents[1] / 'api' / 'resources'
    for filename in ('project.py', 'project_task.py', 'project_task_operational.py', 'process.py'):
        source = (root / filename).read_text(encoding='utf-8')
        assert '@permission_required(' not in source
        assert '@active_company_permission_required(' in source
from types import SimpleNamespace

from api.routes import financial as financial_route


def test_financial_active_company_ignores_client_tenant_selector(monkeypatch):
    app = _app()
    captured_company_ids = []
    expected_company = SimpleNamespace(id=9)
    monkeypatch.setattr(financial_route, 'has_permission', lambda *args: True)
    monkeypatch.setattr(
        financial_route,
        'Company',
        SimpleNamespace(query=SimpleNamespace(get=lambda company_id: captured_company_ids.append(company_id) or expected_company)),
    )

    with app.test_request_context('/financial?company_id=22'):
        session['active_company_id'] = 9
        assert financial_route.get_active_company() is expected_company

    assert captured_company_ids == [9]


def test_financial_resources_and_routes_use_active_company_guard():
    root = Path(__file__).resolve().parents[1]
    for relative_path in (
        'api/resources/financial.py',
        'api/resources/financial_automation.py',
        'api/resources/financial_budget.py',
        'api/routes/financial.py',
        'api/routes/financial_reports.py',
        'api/routes/financial_automation.py',
    ):
        source = (root / relative_path).read_text(encoding='utf-8')
        assert '@permission_required(' not in source
        assert '@active_company_permission_required(' in source
