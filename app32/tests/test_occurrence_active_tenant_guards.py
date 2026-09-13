from types import SimpleNamespace

from flask import Flask, session

from api.resources import occurrence as occurrence_resource
from utils import permissions


def _app():
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.secret_key = 'test'
    return app


def test_occurrence_list_rejects_query_tenant_different_from_active_session(monkeypatch):
    app = _app()
    monkeypatch.setattr(permissions, 'has_permission', lambda *_args: True)

    with app.test_request_context('/api/occurrences?company_id=22'):
        session['active_company_id'] = 9
        payload, status = occurrence_resource.OccurrenceListResource().get()

    assert status == 403
    assert 'não corresponde' in payload['error']


def test_occurrence_request_company_uses_active_session_before_query_selector():
    app = _app()
    with app.test_request_context('/api/occurrences?company_id=22'):
        session['active_company_id'] = 9
        assert occurrence_resource.get_request_company_id() == 9


def test_occurrence_by_id_is_hidden_when_it_belongs_to_another_tenant(monkeypatch):
    app = _app()
    row = SimpleNamespace(company_id=22)
    monkeypatch.setattr(
        occurrence_resource,
        'Occurrence',
        SimpleNamespace(query=SimpleNamespace(get_or_404=lambda occurrence_id: row)),
    )

    with app.test_request_context('/api/occurrences/7'):
        session['active_company_id'] = 9
        assert occurrence_resource._get_occurrence_with_access(7) is None


def test_occurrence_resources_use_active_company_guard():
    resource_methods = (
        occurrence_resource.OccurrenceListResource.get,
        occurrence_resource.OccurrenceListResource.post,
        occurrence_resource.OccurrenceResource.get,
        occurrence_resource.OccurrenceResource.put,
        occurrence_resource.OccurrenceResource.delete,
    )
    assert all(
        getattr(method, '_permission_required', {}).get('active_company_only') is True
        for method in resource_methods
    )
