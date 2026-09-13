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
from api.routes import contracts as contracts_route


def test_contracts_active_company_ignores_client_tenant_selector(monkeypatch):
    app = _app()
    captured_company_ids = []
    expected_company = SimpleNamespace(id=9)
    monkeypatch.setattr(contracts_route, 'has_permission', lambda *args: True)
    monkeypatch.setattr(
        contracts_route,
        'Company',
        SimpleNamespace(query=SimpleNamespace(get=lambda company_id: captured_company_ids.append(company_id) or expected_company)),
    )

    with app.test_request_context('/contracts?company_id=22'):
        session['active_company_id'] = 9
        assert contracts_route.get_active_company() is expected_company

    assert captured_company_ids == [9]


def test_contract_routes_use_active_company_guard():
    source = (Path(__file__).resolve().parents[1] / 'api' / 'routes' / 'contracts.py').read_text(encoding='utf-8')
    assert '@permission_required(' not in source
    assert '@active_company_permission_required(' in source


def test_active_company_permission_rejects_positional_resource_tenant_mismatch(monkeypatch):
    app = _app()
    monkeypatch.setattr(permissions, 'has_permission', lambda *args: True)

    @permissions.active_company_permission_required('companies', 'view')
    def protected(_resource, company_id):
        return {'ok': True}, 200

    with app.test_request_context('/api/companies/22'):
        session['active_company_id'] = 9
        payload, status = protected(object(), 22)

    assert status == 403
    assert 'não corresponde' in payload['error']


def test_company_endpoints_bind_to_active_tenant_and_do_not_use_default_password():
    root = Path(__file__).resolve().parents[1]
    route_source = (root / 'api' / 'routes' / 'companies.py').read_text(encoding='utf-8')
    resource_source = (root / 'api' / 'resources' / 'company.py').read_text(encoding='utf-8')

    assert "@active_company_permission_required('companies', 'edit')\ndef company_edit" in route_source
    assert "@active_company_permission_required('companies', 'edit')\ndef update_performance_settings" in route_source
    assert "@active_company_permission_required('companies', 'view')\ndef get_system_users" in route_source
    assert "User.query.join(Employee, Employee.user_id == User.id)" in route_source
    assert "Employee.company_id == active_company_id" in route_source
    assert "data.get('password', '123456')" not in route_source
    assert "Senha é obrigatória para criar um novo acesso." in route_source
    assert "@active_company_permission_required('companies', 'view')\n    def get(self, company_id):" in resource_source


def test_user_employee_routes_scope_direct_employee_ids_to_active_company():
    source = (Path(__file__).resolve().parents[1] / 'api' / 'user_employee.py').read_text(encoding='utf-8')

    assert "@active_company_permission_required('companies', 'edit')\ndef add_user_to_company" in source
    assert "@active_company_permission_required('companies', 'view')\ndef get_company_employees" in source
    assert source.count('id=employee_id,\n            company_id=active_company_id,') == 2
    assert "else ['phone', 'whatsapp']" in source
    assert "Apenas administradores podem alterar vínculo de usuário" in source


def test_config_and_audit_routes_do_not_allow_query_to_select_tenant():
    root = Path(__file__).resolve().parents[1]
    main_source = (root / 'api' / 'routes' / 'main.py').read_text(encoding='utf-8')
    configs_source = (root / 'api' / 'routes' / 'configs.py').read_text(encoding='utf-8')

    active_resolver = main_source.split('@main_bp.route', 1)[0]
    assert "company_id = session.get('active_company_id')" in active_resolver
    assert "request.args.get('company_id', type=int) or session.get('active_company_id')" not in active_resolver
    assert main_source.count('Empresa da requisição não corresponde à empresa ativa.') >= 1
    assert configs_source.count('Empresa da requisição não corresponde à empresa ativa.') >= 1


def test_dashboard_and_export_routes_require_active_tenant_without_query_override():
    root = Path(__file__).resolve().parents[1]
    main_source = (root / 'api' / 'routes' / 'main.py').read_text(encoding='utf-8')
    configs_source = (root / 'api' / 'routes' / 'configs.py').read_text(encoding='utf-8')

    assert main_source.count('Empresa da requisição não corresponde à empresa ativa.') >= 3
    assert "company_id = request.args.get('company_id', type=int) or session.get('active_company_id')" not in main_source
    assert configs_source.count('Empresa da requisição não corresponde à empresa ativa.') >= 2
