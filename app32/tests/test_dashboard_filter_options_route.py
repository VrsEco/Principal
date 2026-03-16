import os
import sys
from types import SimpleNamespace

from flask import Flask

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api.routes import main as main_route


class _FakeColumn:
    def __init__(self, attr_name):
        self.attr_name = attr_name

    def __eq__(self, other):
        return lambda row: getattr(row, self.attr_name) == other


class _FakeQuery:
    def __init__(self, rows):
        self._rows = list(rows)

    def filter_by(self, **kwargs):
        filtered = self._rows
        for key, value in kwargs.items():
            filtered = [row for row in filtered if getattr(row, key) == value]
        return _FakeQuery(filtered)

    def filter(self, *conditions):
        filtered = self._rows
        for condition in conditions:
            if callable(condition):
                filtered = [row for row in filtered if condition(row)]
        return _FakeQuery(filtered)

    def order_by(self, column):
        attr_name = getattr(column, 'attr_name', 'name')
        return _FakeQuery(sorted(self._rows, key=lambda row: getattr(row, attr_name, '') or ''))

    def all(self):
        return list(self._rows)


def _build_app():
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['LOGIN_DISABLED'] = True
    app.secret_key = 'test'
    app.register_blueprint(main_route.main_bp)
    return app


def test_dashboard_filter_options_includes_active_and_null_status_employees_for_company_admin(monkeypatch):
    app = _build_app()

    companies = [SimpleNamespace(id=1, name='Empresa 1', is_active=True)]
    employees = [
        SimpleNamespace(id=10, company_id=1, name='Ana', status='active'),
        SimpleNamespace(id=11, company_id=1, name='Bruno', status=None),
        SimpleNamespace(id=12, company_id=1, name='Carla', status='inactive'),
    ]
    projects = [SimpleNamespace(id=100, company_id=1, name='Projeto A')]
    processes = [SimpleNamespace(id=200, company_id=1, name='Processo A', code='P.1')]

    monkeypatch.setattr(main_route, 'Company', SimpleNamespace(query=_FakeQuery(companies)))
    monkeypatch.setattr(
        main_route,
        'Employee',
        SimpleNamespace(
            query=_FakeQuery(employees),
            company_id=_FakeColumn('company_id'),
            name=_FakeColumn('name'),
        ),
    )
    monkeypatch.setattr(main_route, 'Project', SimpleNamespace(query=_FakeQuery(projects)))
    monkeypatch.setattr(main_route, 'Process', SimpleNamespace(query=_FakeQuery(processes)))
    monkeypatch.setattr(main_route, 'has_company_full_access', lambda company_id: company_id == 1)
    monkeypatch.setattr(main_route, '_active_employee_filter', lambda: (lambda row: row.status in ('active', None)))

    client = app.test_client()
    response = client.get('/api/dashboard/filter-options?company_id=1')

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['employees'] == [
        {'id': 10, 'name': 'Ana'},
        {'id': 11, 'name': 'Bruno'},
    ]
    assert payload['projects'] == [{'id': 100, 'name': 'Projeto A'}]
    assert payload['processes'] == [{'id': 200, 'name': 'Processo A', 'code': 'P.1'}]
