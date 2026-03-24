import os
import sys
from types import SimpleNamespace

from flask import Flask

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api.resources import process as process_resource


class _FakeCountQuery:
    def __init__(self, count_value):
        self.count_value = count_value
        self.filters = []

    def filter_by(self, **kwargs):
        self.filters.append(kwargs)
        return self

    def count(self):
        return self.count_value


class _FakeSession:
    def __init__(self):
        self.deleted = []
        self.committed = 0
        self.rolled_back = False

    def delete(self, obj):
        self.deleted.append(obj)

    def commit(self):
        self.committed += 1

    def rollback(self):
        self.rolled_back = True


def _build_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'test'
    app.config['TESTING'] = True
    app.config['LOGIN_DISABLED'] = True
    return app


def test_process_delete_returns_conflict_when_linked_records_exist(monkeypatch):
    app = _build_app()
    fake_process = SimpleNamespace(id=77, company_id=12)
    fake_session = _FakeSession()

    routine_query = _FakeCountQuery(2)
    instance_query = _FakeCountQuery(1)
    indicator_query = _FakeCountQuery(3)
    occurrence_query = _FakeCountQuery(0)
    financial_query = _FakeCountQuery(1)

    monkeypatch.setattr(
        process_resource,
        '_get_process_with_access',
        lambda process_id, action='delete', sync_session=True: fake_process,
    )
    monkeypatch.setattr(process_resource, 'Routine', SimpleNamespace(query=routine_query))
    monkeypatch.setattr(process_resource, 'ProcessInstance', SimpleNamespace(query=instance_query))
    monkeypatch.setattr(process_resource, 'Indicator', SimpleNamespace(query=indicator_query))
    monkeypatch.setattr(process_resource, 'Occurrence', SimpleNamespace(query=occurrence_query))
    monkeypatch.setattr(process_resource, 'FinancialAutomationRule', SimpleNamespace(query=financial_query))
    monkeypatch.setattr(process_resource.db, 'session', fake_session)

    with app.test_request_context('/api/processes/77', method='DELETE'):
        response, status = process_resource.ProcessResource().delete.__wrapped__(process_resource.ProcessResource(), 77)

    assert status == 409
    assert response['code'] == 'PROCESS_HAS_LINKED_DATA'
    assert response['details']['process_id'] == 77
    assert response['details']['company_id'] == 12
    assert response['details']['linked_routines_count'] == 2
    assert response['details']['linked_instances_count'] == 1
    assert response['details']['linked_indicators_count'] == 3
    assert response['details']['linked_financial_automations_count'] == 1
    assert 'registros vinculados' in response['error']
    assert fake_session.deleted == []
    assert fake_session.committed == 0

    assert routine_query.filters == [{'company_id': 12, 'process_id': 77}]
    assert instance_query.filters == [{'company_id': 12, 'process_id': 77}]
    assert indicator_query.filters == [{'company_id': 12, 'process_id': 77}]
    assert occurrence_query.filters == [{'company_id': 12, 'process_id': 77}]
    assert financial_query.filters == [{'company_id': 12, 'process_id': 77}]


def test_process_delete_executes_when_no_linked_records_exist(monkeypatch):
    app = _build_app()
    fake_process = SimpleNamespace(id=91, company_id=22)
    fake_session = _FakeSession()

    monkeypatch.setattr(
        process_resource,
        '_get_process_with_access',
        lambda process_id, action='delete', sync_session=True: fake_process,
    )
    monkeypatch.setattr(process_resource, 'Routine', SimpleNamespace(query=_FakeCountQuery(0)))
    monkeypatch.setattr(process_resource, 'ProcessInstance', SimpleNamespace(query=_FakeCountQuery(0)))
    monkeypatch.setattr(process_resource, 'Indicator', SimpleNamespace(query=_FakeCountQuery(0)))
    monkeypatch.setattr(process_resource, 'Occurrence', SimpleNamespace(query=_FakeCountQuery(0)))
    monkeypatch.setattr(process_resource, 'FinancialAutomationRule', SimpleNamespace(query=_FakeCountQuery(0)))
    monkeypatch.setattr(process_resource.db, 'session', fake_session)

    with app.test_request_context('/api/processes/91', method='DELETE'):
        response, status = process_resource.ProcessResource().delete.__wrapped__(process_resource.ProcessResource(), 91)

    assert status == 200
    assert response['message'] == 'Process deleted successfully'
    assert fake_session.deleted == [fake_process]
    assert fake_session.committed == 1


def test_process_architecture_js_handles_delete_failures_gracefully():
    js_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'static', 'js', 'process_architecture.js')
    )
    with open(js_path, 'r', encoding='utf-8') as handle:
        content = handle.read()

    assert 'async function requestDelete(url, confirmMessage)' in content
    assert 'if (!res.ok)' in content
    assert "notifyDeleteError(extractDeleteErrorMessage(payload));" in content
    assert 'await initArchitecture();' in content
