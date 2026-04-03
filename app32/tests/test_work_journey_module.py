import os
import sys
from datetime import date
from types import SimpleNamespace

from flask import Flask

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api.routes import work_journey as work_journey_route
from services.work_journey_helpers import block_chronology_key, clamp_period, rule_matches_date


class _FakeCompanyQuery:
    def __init__(self, company):
        self.company = company

    def get_or_404(self, company_id):
        assert company_id == self.company.id
        return self.company


class _FakeEmployeeQuery:
    def __init__(self, employees):
        self.employees = employees
        self.filters = {}

    def filter_by(self, **kwargs):
        self.filters = kwargs
        return self

    def order_by(self, *args, **kwargs):
        return self

    def all(self):
        return [employee for employee in self.employees if employee.company_id == self.filters.get('company_id') and employee.status == self.filters.get('status')]

    def first(self):
        for employee in self.all():
            if getattr(employee, 'user_id', None) == self.filters.get('user_id'):
                return employee
        return None


class _Column:
    def asc(self):
        return self



def test_rule_matches_date_supports_weekly_monthly_and_annual_ranges():
    assert rule_matches_date('weekly', {'weekdays': [0, 2]}, date(2026, 4, 6)) is True
    assert rule_matches_date('weekly', {'weekdays': [0, 2]}, date(2026, 4, 7)) is False
    assert rule_matches_date('monthly', {'days': [2, 10]}, date(2026, 4, 10)) is True
    assert rule_matches_date('annual', {'start_mmdd': '11-01', 'end_mmdd': '11-15'}, date(2026, 11, 10)) is True
    assert rule_matches_date('annual', {'start_mmdd': '11-01', 'end_mmdd': '11-15'}, date(2026, 11, 20)) is False



def test_clamp_period_returns_expected_ranges():
    start, end = clamp_period('week', date(2026, 4, 8))
    assert start.isoformat() == '2026-04-06'
    assert end.isoformat() == '2026-04-12'

    start, end = clamp_period('month', date(2026, 4, 8))
    assert start.isoformat() == '2026-04-01'
    assert end.isoformat() == '2026-04-30'


def test_block_chronology_key_prioritizes_weekday_then_time():
    blocks = [
        SimpleNamespace(id=3, name='Treinamento', weekdays_json=[4], start_time=SimpleNamespace(hour=9, minute=0), end_time=SimpleNamespace(hour=12, minute=0)),
        SimpleNamespace(id=1, name='Indicadores', weekdays_json=[0], start_time=SimpleNamespace(hour=8, minute=0), end_time=SimpleNamespace(hour=9, minute=0)),
        SimpleNamespace(id=2, name='Processos', weekdays_json=[0], start_time=SimpleNamespace(hour=10, minute=0), end_time=SimpleNamespace(hour=11, minute=0)),
    ]

    ordered = sorted(blocks, key=block_chronology_key)

    assert [block.id for block in ordered] == [1, 2, 3]



def test_work_journey_page_renders_employee_payload(monkeypatch):
    app = Flask(__name__)
    app.secret_key = 'test'
    company = SimpleNamespace(id=9, name='Empresa Teste')
    employees = [
        SimpleNamespace(id=3, company_id=9, user_id=7, status='active', name='Ana', to_dict=lambda: {'id': 3, 'name': 'Ana'}),
        SimpleNamespace(id=4, company_id=9, user_id=8, status='active', name='Bruno', to_dict=lambda: {'id': 4, 'name': 'Bruno'}),
    ]
    captured = {}

    monkeypatch.setattr(work_journey_route, 'Company', SimpleNamespace(query=_FakeCompanyQuery(company)))
    monkeypatch.setattr(
        work_journey_route,
        'Employee',
        SimpleNamespace(query=_FakeEmployeeQuery(employees), name=_Column()),
    )
    monkeypatch.setattr(work_journey_route, 'current_user', SimpleNamespace(id=7, is_authenticated=True))
    monkeypatch.setattr(work_journey_route, 'has_company_full_access', lambda company_id: True)
    monkeypatch.setattr(work_journey_route, 'render_template', lambda template, **ctx: captured.update({'template': template, 'ctx': ctx}) or ctx)

    with app.test_request_context('/companies/9/work-journey'):
        response = work_journey_route._render_work_journey_page(9)

    assert captured['template'] == 'modules/my_work/work_journey.html'
    assert response['selected_employee_id'] == 3
    assert response['employees_payload'][0]['name'] == 'Ana'



def test_templates_expose_work_journey_entrypoints():
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    with open(os.path.join(root, 'templates', 'modules', 'my_work', 'work_journey.html'), 'r', encoding='utf-8') as handle:
        journey_template = handle.read()
    with open(os.path.join(root, 'templates', 'modules', 'my_work', 'my_work_v2.html'), 'r', encoding='utf-8') as handle:
        my_work_template = handle.read()
    with open(os.path.join(root, 'templates', 'routine_details.html'), 'r', encoding='utf-8') as handle:
        routine_app32_template = handle.read()
    with open(os.path.join(root, 'templates', 'legacy', 'routine_details.html'), 'r', encoding='utf-8') as handle:
        routine_legacy_template = handle.read()

    assert 'Jornada Operacional por Blocos' in journey_template
    assert 'Rotinas de processo do colaborador' in journey_template
    assert 'data-tab="agenda"' in journey_template
    assert '/work-journey' in my_work_template
    assert 'Planejamento na Jornada' in routine_app32_template
    assert '/api/routines/${routineId}/journey-bindings' in routine_app32_template
    assert '/api/routines/${routineId}/journey-bindings' in routine_legacy_template
