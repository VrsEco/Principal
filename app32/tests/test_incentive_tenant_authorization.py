from types import SimpleNamespace

from flask import Flask, session

from api.resources import incentive as incentive_resource
from api.routes import incentives as incentive_routes
from services import incentive_access_service
from services.incentive_access_service import IncentiveAccessService


def _app():
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.secret_key = 'test'
    return app


def test_access_service_requires_membership_and_permission(monkeypatch):
    monkeypatch.setattr(incentive_access_service, 'can_access_company', lambda company_id: True)
    monkeypatch.setattr(
        incentive_access_service,
        'has_permission',
        lambda company_id, resource, action: resource == 'incentives' and action == 'view',
    )

    assert IncentiveAccessService.is_allowed(9, 'view') is True
    assert IncentiveAccessService.is_allowed(9, 'edit') is False

    monkeypatch.setattr(incentive_access_service, 'can_access_company', lambda company_id: False)
    assert IncentiveAccessService.is_allowed(9, 'view') is False


def test_blueprint_guard_denies_api_write_without_permission(monkeypatch):
    app = _app()
    seen = []
    monkeypatch.setattr(
        incentive_routes,
        'current_user',
        SimpleNamespace(is_authenticated=True),
    )
    monkeypatch.setattr(
        incentive_routes.IncentiveAccessService,
        'is_allowed',
        lambda company_id, action: seen.append((company_id, action)) or False,
    )

    with app.test_request_context('/api/v1/incentives/facts/10', method='PATCH'):
        session['active_company_id'] = 9
        response, status = incentive_routes.enforce_incentives_tenant_permission()

    assert status == 403
    assert response.get_json()['error'] == 'Permission denied'
    assert seen == [(9, 'edit')]


def test_rule_resource_hides_rule_set_from_other_tenant(monkeypatch):
    app = _app()
    monkeypatch.setattr(
        incentive_resource.IncentiveAccessService,
        'is_allowed',
        lambda company_id, action: company_id == 9 and action == 'view',
    )
    monkeypatch.setattr(
        incentive_resource.IncentiveService,
        'get_rule_set',
        lambda company_id, rule_set_id: None,
    )

    with app.test_request_context('/api/incentives/rule-sets/77/rules'):
        session['active_company_id'] = 9
        payload, status = incentive_resource.IncentiveRuleResource().get(77)

    assert status == 404
    assert payload['error'] == 'Plano de incentivo não encontrado'


def test_calculation_resource_rejects_foreign_rule_set_before_harvest(monkeypatch):
    app = _app()
    monkeypatch.setattr(
        incentive_resource.IncentiveAccessService,
        'is_allowed',
        lambda company_id, action: company_id == 9 and action == 'approve',
    )
    monkeypatch.setattr(
        incentive_resource.IncentiveService,
        'get_rule_set',
        lambda company_id, rule_set_id: None,
    )
    monkeypatch.setattr(
        incentive_resource.IncentiveService,
        'harvest_all_modules',
        lambda *args: (_ for _ in ()).throw(AssertionError('harvest must not run')),
    )

    with app.test_request_context(
        '/api/incentives/calculate',
        method='POST',
        json={
            'rule_set_id': 77,
            'start_date': '2026-09-01',
            'end_date': '2026-09-12',
        },
    ):
        session['active_company_id'] = 9
        payload, status = incentive_resource.IncentiveCalculationResource().post()

    assert status == 404
    assert payload['error'] == 'Plano de incentivo não encontrado'
