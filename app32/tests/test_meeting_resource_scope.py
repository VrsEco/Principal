import os
import sys
from types import SimpleNamespace

from flask import Flask

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api.resources import meeting as meeting_resource


class _FakeMeetingQuery:
    def __init__(self, meeting_obj=None):
        self.meeting_obj = meeting_obj
        self.last_filter_kwargs = None

    def filter_by(self, **kwargs):
        self.last_filter_kwargs = kwargs
        return self

    def first(self):
        return self.meeting_obj


class _FakeCompanyQuery:
    def __init__(self, company=None):
        self.company = company

    def get(self, company_id):
        return self.company

    def filter_by(self, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def first(self):
        return self.company


class _FakeEmployeeQuery:
    def __init__(self, employee=None):
        self.employee = employee
        self.last_filter_kwargs = None

    def filter_by(self, **kwargs):
        self.last_filter_kwargs = kwargs
        return self

    def first(self):
        return self.employee


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
    return app


def test_get_request_company_id_prefers_query_arg(monkeypatch):
    app = _build_app()
    monkeypatch.setattr(meeting_resource, 'current_user', SimpleNamespace(is_authenticated=True, id=9, role='collaborator'))
    monkeypatch.setattr(meeting_resource, 'Employee', SimpleNamespace(query=_FakeEmployeeQuery(SimpleNamespace(company_id=33))))

    with app.test_request_context('/meetings/api/meeting/5?company_id=12'):
        assert meeting_resource.get_request_company_id() == 12


def test_get_meeting_or_404_filters_by_company(monkeypatch):
    app = _build_app()
    fake_meeting = SimpleNamespace(id=5, company_id=12)
    fake_query = _FakeMeetingQuery(fake_meeting)
    monkeypatch.setattr(meeting_resource, 'current_user', SimpleNamespace(is_authenticated=True, id=9, role='collaborator'))
    monkeypatch.setattr(meeting_resource, 'Meeting', SimpleNamespace(query=fake_query))
    monkeypatch.setattr(meeting_resource, 'Company', SimpleNamespace(query=_FakeCompanyQuery(SimpleNamespace(id=12, is_active=True))))
    monkeypatch.setattr(meeting_resource, 'Company', SimpleNamespace(query=_FakeCompanyQuery(SimpleNamespace(id=12, is_active=True))))
    monkeypatch.setattr(meeting_resource, 'Employee', SimpleNamespace(query=_FakeEmployeeQuery(SimpleNamespace(company_id=12))))

    with app.test_request_context('/meetings/api/meeting/5?company_id=12'):
        meeting, error = meeting_resource.get_meeting_or_404(5)

    assert error is None
    assert meeting is fake_meeting
    assert fake_query.last_filter_kwargs == {'id': 5, 'company_id': 12}


def test_meeting_delete_uses_company_scope_and_deletes(monkeypatch):
    app = _build_app()
    fake_meeting = SimpleNamespace(id=5, company_id=12)
    fake_query = _FakeMeetingQuery(fake_meeting)
    fake_session = _FakeSession()

    monkeypatch.setattr(meeting_resource, 'current_user', SimpleNamespace(is_authenticated=True, id=9, role='collaborator'))
    monkeypatch.setattr(meeting_resource, 'Meeting', SimpleNamespace(query=fake_query))
    monkeypatch.setattr(meeting_resource, 'Company', SimpleNamespace(query=_FakeCompanyQuery(SimpleNamespace(id=12, is_active=True))))
    monkeypatch.setattr(meeting_resource, 'Employee', SimpleNamespace(query=_FakeEmployeeQuery(SimpleNamespace(company_id=12))))
    monkeypatch.setattr(meeting_resource.db, 'session', fake_session)

    with app.test_request_context('/meetings/api/meeting/5?company_id=12', method='DELETE'):
        response = meeting_resource.MeetingResource().delete.__wrapped__(meeting_resource.MeetingResource(), 5)

    assert response['success'] is True
    assert fake_query.last_filter_kwargs == {'id': 5, 'company_id': 12}
    assert fake_session.deleted == [fake_meeting]
    assert fake_session.committed == 1


def test_meetings_template_contains_delete_action():
    template_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'templates', 'meetings_manage.html'))
    with open(template_path, 'r', encoding='utf-8') as handle:
        content = handle.read()

    assert 'btn-excluir-reuniao-editor' in content
    assert 'window.excluirReuniao = excluirReuniao;' in content
    assert "method: 'DELETE'" in content


def test_get_meeting_or_404_returns_403_when_company_not_accessible(monkeypatch):
    app = _build_app()
    monkeypatch.setattr(meeting_resource, 'current_user', SimpleNamespace(is_authenticated=True, id=9, role='collaborator'))
    monkeypatch.setattr(meeting_resource, 'Company', SimpleNamespace(query=_FakeCompanyQuery(SimpleNamespace(id=12, is_active=True))))
    monkeypatch.setattr(meeting_resource, 'Employee', SimpleNamespace(query=_FakeEmployeeQuery(None)))
    monkeypatch.setattr(meeting_resource, 'Meeting', SimpleNamespace(query=_FakeMeetingQuery(SimpleNamespace(id=5, company_id=12))))

    with app.test_request_context('/meetings/api/meeting/5?company_id=12'):
        meeting, error = meeting_resource.get_meeting_or_404(5)

    assert meeting is None
    assert error[1] == 403
    assert 'não tem acesso' in error[0]['message']
