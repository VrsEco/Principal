from flask import Flask, session

from api.resources import operational_audit as audit_resource
from utils import permissions


def _app():
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.secret_key = 'test'
    return app


def test_operational_audit_rejects_query_tenant_different_from_active_session(monkeypatch):
    app = _app()
    monkeypatch.setattr(permissions, 'has_permission', lambda *_args: True)

    with app.test_request_context('/api/operations/audit?company_id=22'):
        session['active_company_id'] = 9
        payload, status = audit_resource.OperationalAuditPanelResource().get()

    assert status == 403
    assert 'não corresponde' in payload['error']


def test_operational_audit_uses_active_company_guard():
    metadata = getattr(audit_resource.OperationalAuditPanelResource.get, '_permission_required', {})
    assert metadata == {
        'resource': 'financial',
        'action': 'view',
        'active_company_only': True,
    }
