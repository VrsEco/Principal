import os
import sys
from datetime import date, time
from types import SimpleNamespace

from flask import Flask

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api.routes import work_journey as work_journey_route
from services import work_journey_agenda_presenter
from services import work_journey_service
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


class _FakeSession:
    def add(self, *_args, **_kwargs):
        return None

    def commit(self):
        return None


class _FakeBlockQuery:
    def filter_by(self, **_kwargs):
        return self

    def first(self):
        return None


class _FakeCompanyLookup:
    def __init__(self, company):
        self.company = company

    def get(self, company_id):
        assert company_id == self.company.id
        return self.company



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


def test_save_block_respects_empty_accepted_item_types(monkeypatch):
    fake_employee = SimpleNamespace(id=3)

    class _FakeBlock:
        query = _FakeBlockQuery()

        def __init__(self, company_id=None, employee_id=None):
            self.company_id = company_id
            self.employee_id = employee_id

        def to_dict(self):
            return {'accepted_item_types': list(self.accepted_item_types or [])}

    monkeypatch.setattr(work_journey_service, 'ensure_employee', lambda company_id, employee_id: fake_employee)
    monkeypatch.setattr(work_journey_service, 'WorkJourneyBlock', _FakeBlock)
    monkeypatch.setattr(work_journey_service, 'db', SimpleNamespace(session=_FakeSession()))

    payload = {
        'employee_id': 3,
        'name': 'Meditação',
        'description': 'Meditação e estudo',
        'start_time': '08:00',
        'end_time': '09:00',
        'block_mode': 'reserved_full',
        'weekdays': [0, 1, 2, 3, 4],
        'accepted_item_types': [],
        'order_index': 0,
        'is_active': True,
    }

    result = work_journey_service.save_block(9, payload)

    assert result['accepted_item_types'] == []


def test_serialize_item_adds_app32_display_code(monkeypatch):
    fake_company = SimpleNamespace(id=9, client_code='AA', name='Alpha')
    monkeypatch.setattr(work_journey_service, 'Company', SimpleNamespace(query=_FakeCompanyLookup(fake_company)))

    manual_item = SimpleNamespace(
        id=1241,
        company_id=9,
        item_type='manual',
        source_id=None,
        rule_id=None,
        title='Almoço com fulano de tal',
        status='pending',
        due_date=date(2026, 4, 3),
        block=SimpleNamespace(name='Meditação'),
        metadata_json={},
        to_dict=lambda: {'id': 1241, 'title': 'Almoço com fulano de tal', 'status': 'pending', 'due_date': '2026-04-03', 'metadata_json': {}},
    )

    payload = work_journey_service.serialize_item(manual_item)

    assert payload['display_code'] == 'AA.V.1241'
    assert payload['display_title'] == 'AA.V.1241 - Almoço com fulano de tal'


def test_templates_expose_work_journey_entrypoints():
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    with open(os.path.join(root, 'templates', 'modules', 'my_work', 'work_journey.html'), 'r', encoding='utf-8') as handle:
        journey_template = handle.read()
    with open(os.path.join(root, 'templates', 'modules', 'my_work', '_agendas_panel.html'), 'r', encoding='utf-8') as handle:
        agendas_panel = handle.read()
    with open(os.path.join(root, 'templates', 'modules', 'my_work', 'my_work_v2.html'), 'r', encoding='utf-8') as handle:
        my_work_template = handle.read()
    with open(os.path.join(root, 'templates', 'routine_details.html'), 'r', encoding='utf-8') as handle:
        routine_app32_template = handle.read()
    with open(os.path.join(root, 'templates', 'legacy', 'routine_details.html'), 'r', encoding='utf-8') as handle:
        routine_legacy_template = handle.read()

    assert 'Agendas da Jornada' in journey_template
    assert 'data-tab="agendas"' in journey_template
    assert 'work-journey-agendas.js' in journey_template
    assert 'work-journey-agendas-render.js' in journey_template
    assert 'Kanban de agendas' in agendas_panel
    assert 'agendaBoardContainer' in agendas_panel
    assert 'agendaUnassignedContainer' in agendas_panel
    assert 'agendaLockBtn' in agendas_panel
    assert 'agendaPdfBtn' in agendas_panel
    assert '/work-journey' in my_work_template
    assert 'Planejamento na Jornada' in routine_app32_template
    assert '/api/routines/${routineId}/journey-bindings' in routine_app32_template
    assert '/api/routines/${routineId}/journey-bindings' in routine_legacy_template


def test_agenda_presenter_materializes_reserved_and_operational_blocks(monkeypatch):
    monkeypatch.setattr(work_journey_agenda_presenter, 'build_item_display_code', lambda item: 'AA.IP.1')

    agenda = SimpleNamespace(
        id=1,
        company_id=9,
        employee_id=3,
        anchor_date=date(2026, 4, 6),
        scope='week',
        status='suggested',
        engine_version='agendas-v1',
        summary_json={},
    )
    employee = SimpleNamespace(name='Ana', to_dict=lambda: {'id': 3, 'name': 'Ana'})
    op_block = SimpleNamespace(
        id=10,
        name='Operacional',
        description='Bloco operacional',
        start_time=time(8, 0),
        end_time=time(9, 0),
        block_mode='operational',
        weekdays_json=[0],
    )
    reserved_block = SimpleNamespace(
        id=11,
        name='Meditação',
        description='Bloco reservado',
        start_time=time(9, 0),
        end_time=time(10, 0),
        block_mode='reserved_full',
        weekdays_json=[0],
    )
    source_item = SimpleNamespace(
        id=21,
        company_id=9,
        item_type='process_instance',
        source_id=77,
        title='Checar rotina',
        description='Descrição',
        status='pending',
        priority='normal',
        due_date=date(2026, 4, 6),
        occurrence_date=date(2026, 4, 6),
        worked_minutes=0,
        estimated_minutes=30,
        metadata_json={'source_label': 'Rotina', 'source_url': '/x'},
        block=None,
    )
    agenda_entry = SimpleNamespace(
        id=1,
        agenda_id=1,
        company_id=9,
        employee_id=3,
        journey_item_id=21,
        block_id=10,
        planned_date=date(2026, 4, 6),
        position_index=0,
        allocated_minutes=30,
        planned_start_minutes=480,
        planned_end_minutes=510,
        overflow_minutes=0,
        is_fixed=False,
        is_over_capacity=False,
        manual_override=False,
        metadata_json={},
        block=op_block,
        journey_item=source_item,
    )
    reserved_entry = SimpleNamespace(
        id=2,
        agenda_id=1,
        company_id=9,
        employee_id=3,
        journey_item_id=22,
        block_id=11,
        planned_date=date(2026, 4, 6),
        position_index=1,
        allocated_minutes=0,
        planned_start_minutes=None,
        planned_end_minutes=None,
        overflow_minutes=0,
        is_fixed=False,
        is_over_capacity=False,
        manual_override=False,
        metadata_json={},
        block=reserved_block,
        journey_item=SimpleNamespace(
            id=22,
            company_id=9,
            item_type='manual',
            source_id=None,
            title='Meditar',
            description='',
            status='pending',
            priority='normal',
            due_date=date(2026, 4, 6),
            occurrence_date=date(2026, 4, 6),
            worked_minutes=0,
            estimated_minutes=0,
            metadata_json={},
            block=None,
        ),
    )

    payload = work_journey_agenda_presenter.serialize_agenda_payload(
        agenda,
        employee,
        [op_block, reserved_block],
        [agenda_entry, reserved_entry],
    )

    assert payload['employee_name'] == 'Ana'
    assert payload['days'][0]['label'] == '06/04/2026'
    assert payload['days'][0]['subtitle'] == 'Seg'
    assert payload['days'][0]['blocks'][0]['planned_minutes'] == 30
    assert payload['days'][0]['blocks'][1]['planned_minutes'] == 60
    assert payload['unassigned_items'] == []
