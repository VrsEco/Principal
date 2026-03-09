import os
import sys
from types import SimpleNamespace

from flask import Flask

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api.routes import meetings as meetings_route


class _FakeEmployeeQuery:
    def __init__(self, matches=None):
        self.matches = matches or {}
        self.last_filter_kwargs = None

    def filter_by(self, **kwargs):
        self.last_filter_kwargs = kwargs
        return self

    def first(self):
        key = (
            self.last_filter_kwargs.get('user_id'),
            self.last_filter_kwargs.get('company_id'),
            self.last_filter_kwargs.get('status'),
        )
        return self.matches.get(key)

    def order_by(self, *args, **kwargs):
        return self


class _FakeCompanyQuery:
    def __init__(self, companies=None):
        self.companies = companies or {}

    def get(self, company_id):
        return self.companies.get(company_id)

    def get_or_404(self, company_id):
        company = self.companies.get(company_id)
        if not company:
            raise RuntimeError('not found')
        return company

    def filter_by(self, **kwargs):
        self._filtered = kwargs
        return self

    def order_by(self, *args, **kwargs):
        return self

    def first(self):
        for company in self.companies.values():
            if getattr(company, 'is_active', True):
                return company
        return None


class _FakeMeetingQuery:
    def __init__(self):
        self.filter_kwargs = None

    def filter_by(self, **kwargs):
        self.filter_kwargs = kwargs
        return self

    def order_by(self, *args, **kwargs):
        return self

    def all(self):
        return []

    def first_or_404(self):
        return SimpleNamespace(to_dict=lambda: {'id': 5, 'company_id': self.filter_kwargs['company_id']})


class _FakeListQuery:
    def filter_by(self, **kwargs):
        return self

    def all(self):
        return []


class _FakeColumn:
    def asc(self):
        return self


def _build_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'test'
    return app


def test_user_can_access_company_for_employee(monkeypatch):
    monkeypatch.setattr(meetings_route, 'current_user', SimpleNamespace(id=8, is_authenticated=True, role='user'))
    monkeypatch.setattr(meetings_route, 'Company', SimpleNamespace(query=_FakeCompanyQuery({12: SimpleNamespace(id=12, is_active=True)})))
    monkeypatch.setattr(
        meetings_route,
        'Employee',
        SimpleNamespace(query=_FakeEmployeeQuery({(8, 12, 'active'): SimpleNamespace(company_id=12)})),
    )

    assert meetings_route.user_can_access_company(12) is True
    assert meetings_route.user_can_access_company(99) is False


def test_meetings_company_manage_blocks_cross_company_access(monkeypatch):
    app = _build_app()
    monkeypatch.setattr(meetings_route, 'current_user', SimpleNamespace(id=8, is_authenticated=True, role='user'))
    monkeypatch.setattr(meetings_route, 'Company', SimpleNamespace(query=_FakeCompanyQuery({1: SimpleNamespace(id=1, is_active=True, to_dict=lambda: {'id': 1})})))
    monkeypatch.setattr(meetings_route, 'Employee', SimpleNamespace(query=_FakeEmployeeQuery({})))

    with app.test_request_context('/meetings/company/1'):
        try:
            meetings_route.meetings_company_manage.__wrapped__(1)
        except Exception as exc:
            assert getattr(exc, 'code', None) == 403
        else:
            raise AssertionError('expected 403')


def test_meeting_report_blocks_cross_company_access(monkeypatch):
    app = _build_app()
    monkeypatch.setattr(meetings_route, 'current_user', SimpleNamespace(id=8, is_authenticated=True, role='user'))
    monkeypatch.setattr(meetings_route, 'Company', SimpleNamespace(query=_FakeCompanyQuery({1: SimpleNamespace(id=1, is_active=True, to_dict=lambda: {'id': 1})})))
    monkeypatch.setattr(meetings_route, 'Employee', SimpleNamespace(query=_FakeEmployeeQuery({})))
    monkeypatch.setattr(meetings_route, 'Meeting', SimpleNamespace(query=_FakeMeetingQuery()))

    with app.test_request_context('/meetings/company/1/meeting/5/report'):
        try:
            meetings_route.meeting_report.__wrapped__(1, 5)
        except Exception as exc:
            assert getattr(exc, 'code', None) == 403
        else:
            raise AssertionError('expected 403')
