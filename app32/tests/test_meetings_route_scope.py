import os
import sys
from types import SimpleNamespace

from flask import Flask

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api.routes import meetings as meetings_route


class _FakeEmployeeQuery:
    def __init__(self, matches=None, employees=None):
        self.matches = matches or {}
        self.employees = employees or []
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

    def all(self):
        company_id = self.last_filter_kwargs.get('company_id')
        status = self.last_filter_kwargs.get('status')
        return [
            employee
            for employee in self.employees
            if (company_id is None or getattr(employee, 'company_id', None) == company_id)
            and (status is None or getattr(employee, 'status', None) == status)
        ]


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


class _FakeProjectQuery:
    def __init__(self, projects=None):
        self.projects = projects or []
        self.last_filter_kwargs = None

    def filter_by(self, **kwargs):
        self.last_filter_kwargs = kwargs
        return self

    def all(self):
        company_id = self.last_filter_kwargs.get('company_id')
        return [project for project in self.projects if getattr(project, 'company_id', None) == company_id]


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


def test_meeting_report_enriches_activity_project_titles(monkeypatch):
    app = _build_app()
    captured = {}

    company_obj = SimpleNamespace(id=1, is_active=True, to_dict=lambda: {'id': 1, 'name': 'Empresa Teste'})
    meeting_payload = {
        'id': 5,
        'company_id': 1,
        'project_id': 11,
        'project_title': 'Projeto Base',
        'project_code': 'PB.1',
        'activities': [
            {'title': 'Atividade A', 'project_id': 22},
            {'title': 'Atividade B', 'project_id': 11},
            {'title': 'Atividade C'},
        ],
    }

    class _SingleMeetingQuery:
        def __init__(self, meeting_obj):
            self.meeting_obj = meeting_obj
            self.filter_kwargs = None

        def filter_by(self, **kwargs):
            self.filter_kwargs = kwargs
            return self

        def first_or_404(self):
            return self.meeting_obj

    def _fake_render(template_name, **context):
        captured['template_name'] = template_name
        captured['context'] = context
        return context

    monkeypatch.setattr(meetings_route, 'current_user', SimpleNamespace(id=1, is_authenticated=True, role='admin'))
    monkeypatch.setattr(meetings_route, 'Company', SimpleNamespace(query=_FakeCompanyQuery({1: company_obj})))
    monkeypatch.setattr(
        meetings_route,
        'Employee',
        SimpleNamespace(
            query=_FakeEmployeeQuery(
                {},
                employees=[
                    SimpleNamespace(
                        id=1,
                        company_id=1,
                        status='active',
                        name='Ana',
                        email='ana@empresa.com',
                        phone='7133334444',
                        whatsapp='71999990000',
                    )
                ],
            )
        ),
    )
    monkeypatch.setattr(
        meetings_route,
        'Meeting',
        SimpleNamespace(query=_SingleMeetingQuery(SimpleNamespace(to_dict=lambda: meeting_payload))),
    )
    monkeypatch.setattr(
        meetings_route,
        'Project',
        SimpleNamespace(
            query=_FakeProjectQuery(
                [
                    SimpleNamespace(id=22, company_id=1, name='Projeto Comercial', code='PC.22'),
                    SimpleNamespace(id=11, company_id=1, name='Projeto Base', code='PB.1'),
                    SimpleNamespace(id=99, company_id=2, name='Projeto Externo', code='PE.99'),
                ]
            )
        ),
    )
    monkeypatch.setattr(meetings_route, 'render_template', _fake_render)

    with app.test_request_context('/meetings/company/1/meeting/5/report'):
        result = meetings_route.meeting_report.__wrapped__(1, 5)

    assert result == captured['context']
    assert captured['template_name'] == 'report_pdf.html'
    assert captured['context']['meeting']['activities'][0]['project_title'] == 'Projeto Comercial'
    assert captured['context']['meeting']['activities'][0]['project_code'] == 'PC.22'
    assert captured['context']['meeting']['activities'][1]['project_title'] == 'Projeto Base'
    assert captured['context']['meeting']['activities'][1]['project_code'] == 'PB.1'
    assert 'project_title' not in captured['context']['meeting']['activities'][2]
    assert captured['context']['report']['title'] == 'Sem título'
    assert captured['context']['report']['participants'] == []
