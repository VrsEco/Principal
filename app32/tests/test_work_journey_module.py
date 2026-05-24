from collections import defaultdict
import os
import sys
from datetime import date, datetime, time
from types import SimpleNamespace

from flask import Flask

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api.resources import meeting as meeting_resource
from api.resources import process as process_resource
from api.routes import work_journey_agendas as work_journey_agendas_route
from api.routes import work_journey as work_journey_route
from api.routes import work_journey_report as work_journey_report_route
from services import work_journey_agenda_engine
from services import work_journey_agenda_presenter
from services import work_journey_agenda_service
from services import work_calendar_event_service
from services import process_execution_projection_service
from services import work_journey_report_service
from services import work_journey_service
from services import work_journey_sync
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


class _FakeAgendaMoveQuery:
    def __init__(self, entry):
        self.entry = entry
        self.filters = {}

    def options(self, *_args, **_kwargs):
        return self

    def filter_by(self, **kwargs):
        self.filters = kwargs
        return self

    def first(self):
        if not self.entry:
            return None
        if self.filters.get('company_id') != getattr(self.entry, 'company_id', None):
            return None
        if self.filters.get('employee_id') != getattr(self.entry, 'employee_id', None):
            return None
        if self.filters.get('id') != getattr(self.entry, 'id', None):
            return None
        return self.entry


class _FakeAgendaQuery:
    def filter_by(self, **_kwargs):
        return self

    def first(self):
        return None


class _AgendaCurrentWeekDate(date):
    @classmethod
    def today(cls):
        return cls(2026, 4, 9)


class _FakeCompanyLookup:
    def __init__(self, company):
        self.company = company

    def get(self, company_id):
        assert company_id == self.company.id
        return self.company


class _FixedDate(date):
    @classmethod
    def today(cls):
        return cls(2026, 4, 4)



def test_rule_matches_date_supports_weekly_monthly_and_annual_ranges():
    assert rule_matches_date('weekly', {'weekdays': [0, 2]}, date(2026, 4, 6)) is True
    assert rule_matches_date('weekly', {'weekdays': [0, 2]}, date(2026, 4, 7)) is False
    assert rule_matches_date('monthly', {'days': [2, 10]}, date(2026, 4, 10)) is True
    assert rule_matches_date('annual', {'start_mmdd': '11-01', 'end_mmdd': '11-15'}, date(2026, 11, 10)) is True
    assert rule_matches_date('annual', {'start_mmdd': '11-01', 'end_mmdd': '11-15'}, date(2026, 11, 20)) is False



def test_clamp_period_returns_expected_ranges():
    start, end = clamp_period('week', date(2026, 4, 8))
    assert start.isoformat() == '2026-04-05'
    assert end.isoformat() == '2026-04-11'

    start, end = clamp_period('month', date(2026, 4, 8))
    assert start.isoformat() == '2026-04-01'
    assert end.isoformat() == '2026-04-30'


def test_project_summary_aggregates_hours_counts_and_next_due():
    row = {
        'status': 'in_progress',
        'block_names': ['Bloco A', 'Bloco B'],
        'responsible_activities': [
            {'task_id': 1, 'estimated_hours': 3, 'due_date': '2026-04-10'},
            {'task_id': 2, 'estimated_hours': 2.5, 'due_date': '2026-04-08'},
        ],
        'participating_activities': [
            {'task_id': 3, 'estimated_hours': 1.5, 'due_date': '2026-04-12'},
        ],
    }

    summary = work_journey_report_service._summarize_project_row(row)

    assert summary['responsible_count'] == 2
    assert summary['participating_count'] == 1
    assert summary['total_count'] == 3
    assert summary['responsible_hours'] == 5.5
    assert summary['participating_hours'] == 1.5
    assert summary['total_hours'] == 7.0
    assert summary['next_due'] == '2026-04-08'
    assert summary['next_due_label'] == '08/04/2026'
    assert summary['blocks_label'] == 'Bloco A, Bloco B'


def test_report_service_event_minutes_uses_window_or_metadata():
    timed_event = SimpleNamespace(start_time=time(9, 0), end_time=time(10, 15), metadata_json={})
    metadata_event = SimpleNamespace(start_time=None, end_time=None, metadata_json={'duration_minutes': 45})

    assert work_journey_report_service._event_minutes(timed_event) == 75
    assert work_journey_report_service._event_minutes(metadata_event) == 45


def test_calendar_event_serialization_exposes_owner_creator_and_executor(monkeypatch):
    monkeypatch.setattr(
        work_calendar_event_service,
        '_resolve_source_context',
        lambda company_id, source_type, source_id: {
            'source_label': 'Instância de processo',
            'source_code': 'IP.501',
            'source_title': 'Fechamento mensal',
            'source_url': '/companies/9/process-instances?instance_id=501',
            'source_owner_employee_id': 8,
            'source_owner_employee_name': 'Bruno',
        },
    )
    monkeypatch.setattr(
        work_calendar_event_service,
        '_employee_name',
        lambda company_id, employee_id: {3: 'Ana', 8: 'Bruno', 11: 'Carla'}.get(employee_id),
    )

    event = SimpleNamespace(
        id=91,
        company_id=9,
        employee_id=3,
        employee=SimpleNamespace(name='Ana'),
        block=None,
        source_type='process_instance',
        source_id=501,
        title='Revisar instância',
        description='Acompanhamento operacional',
        event_date=date(2026, 5, 4),
        start_time=time(9, 0),
        end_time=time(10, 0),
        status='confirmed',
        priority='high',
        execution_notes='Registrar Horas/Info depois',
        metadata_json={'responsible_employee_id': 11, 'responsible_employee_name': 'Carla'},
        created_by_user=SimpleNamespace(name='Fabiano'),
        to_dict=lambda: {
            'id': 91,
            'company_id': 9,
            'employee_id': 3,
            'source_type': 'process_instance',
            'source_id': 501,
            'title': 'Revisar instância',
            'event_date': '2026-05-04',
            'start_time': '09:00',
            'end_time': '10:00',
            'status': 'confirmed',
            'priority': 'high',
            'metadata_json': {'responsible_employee_id': 11, 'responsible_employee_name': 'Carla'},
        },
    )

    payload = work_calendar_event_service.serialize_calendar_event(event)

    assert payload['owner_employee_id'] == 3
    assert payload['owner_employee_name'] == 'Ana'
    assert payload['created_by_user_name'] == 'Fabiano'
    assert payload['responsible_employee_id'] == 11
    assert payload['responsible_employee_name'] == 'Carla'
    assert payload['executor_employee_id'] == 11
    assert payload['source_owner_employee_id'] == 8
    assert payload['source_owner_employee_name'] == 'Bruno'


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
    assert response['selected_employee_name'] == 'Ana'


def test_work_journey_page_uses_source_suggested_employee_when_available(monkeypatch):
    app = Flask(__name__)
    app.secret_key = 'test'
    company = SimpleNamespace(id=9, name='Empresa Teste')
    employees = [
        SimpleNamespace(id=4, company_id=9, user_id=8, status='active', name='Bruno', to_dict=lambda: {'id': 4, 'name': 'Bruno'}),
    ]
    captured = {}

    monkeypatch.setattr(work_journey_route, 'Company', SimpleNamespace(query=_FakeCompanyQuery(company)))
    monkeypatch.setattr(
        work_journey_route,
        'Employee',
        SimpleNamespace(query=_FakeEmployeeQuery(employees), name=_Column()),
    )
    monkeypatch.setattr(work_journey_route, 'current_user', SimpleNamespace(id=99, is_authenticated=True))
    monkeypatch.setattr(work_journey_route, 'has_company_full_access', lambda company_id: True)
    monkeypatch.setattr(work_journey_route, 'suggest_employee_for_source', lambda company_id, source_type, source_id: 4)
    monkeypatch.setattr(work_journey_route, 'render_template', lambda template, **ctx: captured.update({'template': template, 'ctx': ctx}) or ctx)

    with app.test_request_context('/companies/9/calendar?source_type=project_task&source_id=501'):
        response = work_journey_route._render_work_journey_page(9)

    assert response['selected_employee_id'] == 4
    assert response['source_type'] == 'project_task'
    assert response['source_id'] == 501


def test_work_journey_page_hides_selector_for_non_manager(monkeypatch):
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
    monkeypatch.setattr(work_journey_route, 'has_company_full_access', lambda company_id: False)
    monkeypatch.setattr(work_journey_route, 'render_template', lambda template, **ctx: captured.update({'template': template, 'ctx': ctx}) or ctx)

    with app.test_request_context('/companies/9/calendar?employee_id=4'):
        response = work_journey_route._render_work_journey_page(9)

    assert response['selected_employee_id'] == 3
    assert response['selected_employee_name'] == 'Ana'
    assert response['employees_payload'] == [{'id': 3, 'name': 'Ana'}]
    assert response['can_manage_all'] is False


def test_client_calendar_scope_includes_self_and_collaborators_only(monkeypatch):
    app = Flask(__name__)
    app.secret_key = 'test'
    company = SimpleNamespace(id=9, name='Empresa Teste')
    employees = [
        SimpleNamespace(id=3, company_id=9, user_id=7, user_role='client', status='active', name='Cliente Atual', to_dict=lambda: {'id': 3, 'name': 'Cliente Atual'}),
        SimpleNamespace(id=4, company_id=9, user_id=8, user_role='user', status='active', name='Colaborador', to_dict=lambda: {'id': 4, 'name': 'Colaborador'}),
        SimpleNamespace(id=5, company_id=9, user_id=9, user_role='client', status='active', name='Outro Cliente', to_dict=lambda: {'id': 5, 'name': 'Outro Cliente'}),
        SimpleNamespace(id=6, company_id=9, user_id=10, user_role='admin', status='active', name='Administrador', to_dict=lambda: {'id': 6, 'name': 'Administrador'}),
    ]
    captured = {}

    monkeypatch.setattr(work_journey_route, 'Company', SimpleNamespace(query=_FakeCompanyQuery(company)))
    monkeypatch.setattr(
        work_journey_route,
        'Employee',
        SimpleNamespace(query=_FakeEmployeeQuery(employees), name=_Column()),
    )
    monkeypatch.setattr(work_journey_route, 'current_user', SimpleNamespace(id=7, role='client', is_authenticated=True))
    monkeypatch.setattr(work_journey_route, 'has_company_full_access', lambda company_id: True)
    monkeypatch.setattr(work_journey_route, 'render_template', lambda template, **ctx: captured.update({'template': template, 'ctx': ctx}) or ctx)

    with app.test_request_context('/companies/9/calendar'):
        response = work_journey_route._render_work_journey_page(9)

    assert response['selected_employee_id'] == 3
    assert [employee['id'] for employee in response['employees_payload']] == [3, 4]
    assert response['can_manage_all'] is True
    assert work_journey_route._can_manage_employee(9, 3, employee=employees[0]) is True
    assert work_journey_route._can_manage_employee(9, 4, employee=employees[1]) is True
    assert work_journey_route._can_manage_employee(9, 5, employee=employees[2]) is False
    assert work_journey_route._can_manage_employee(9, 6, employee=employees[3]) is False


def test_work_journey_page_respects_requested_anchor_date(monkeypatch):
    app = Flask(__name__)
    app.secret_key = 'test'
    company = SimpleNamespace(id=9, name='Empresa Teste')
    employees = [
        SimpleNamespace(id=3, company_id=9, user_id=7, status='active', name='Ana', to_dict=lambda: {'id': 3, 'name': 'Ana'}),
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

    with app.test_request_context('/companies/9/calendar?date=2026-05-12'):
        response = work_journey_route._render_work_journey_page(9)

    assert response['today'] == '2026-05-12'


def test_report_page_exposes_pdf_url(monkeypatch):
    app = Flask(__name__)
    app.secret_key = 'test'
    app.add_url_rule(
        '/companies/<int:company_id>/work-journey/export-pdf',
        endpoint='work_journey_report.work_journey_report_pdf',
        view_func=lambda company_id: f'pdf-{company_id}',
    )
    captured = {}

    monkeypatch.setattr(
        work_journey_report_route,
        '_build_report_payload',
        lambda company_id: (
            SimpleNamespace(id=company_id, name='Empresa Teste'),
            {
                'summary': {'scope_label': 'Empresa inteira'},
                'period': {'week_label': '05/04 a 11/04', 'month_label': '04/2026'},
                'filters': {'departments': [], 'department': None, 'employees': [], 'employee_id': None},
                'charts': {},
                'benchmarks': {},
                'rankings': {'occupation': [], 'availability': [], 'block_pressure': []},
                'insights': [],
                'employees': [],
            },
            True,
        ),
    )
    monkeypatch.setattr(
        work_journey_report_route,
        'render_template',
        lambda template, **ctx: captured.update({'template': template, 'ctx': ctx}) or ctx,
    )

    with app.test_request_context('/companies/9/work-journey/report?employee_id=3&date=2026-04-05'):
        response = work_journey_report_route.work_journey_report_page.__wrapped__(9)

    assert captured['template'] == 'modules/my_work/work_journey_report.html'
    assert response['pdf_url'] == '/companies/9/work-journey/export-pdf?employee_id=3&date=2026-04-05&layout=landscape'
    assert response['pdf_landscape_url'] == '/companies/9/work-journey/export-pdf?employee_id=3&date=2026-04-05&layout=landscape'
    assert response['pdf_portrait_url'] == '/companies/9/work-journey/export-pdf?employee_id=3&date=2026-04-05&layout=portrait'


def test_report_pdf_page_renders_print_template(monkeypatch):
    app = Flask(__name__)
    app.secret_key = 'test'
    captured = {}

    monkeypatch.setattr(
        work_journey_report_route,
        '_build_report_payload',
        lambda company_id: (
            SimpleNamespace(id=company_id, name='Empresa Teste'),
            {
                'summary': {'scope_label': 'Empresa inteira'},
                'period': {'week_label': '05/04 a 11/04', 'month_label': '04/2026'},
                'employees': [],
                'rankings': {'occupation': [], 'availability': [], 'block_pressure': []},
                'insights': [],
                'charts': {'scope_mix': {'values': [0, 0, 0, 0, 0, 0, 0]}},
            },
            True,
        ),
    )
    monkeypatch.setattr(
        work_journey_report_route,
        'render_template',
        lambda template, **ctx: captured.update({'template': template, 'ctx': ctx}) or ctx,
    )

    with app.test_request_context('/companies/9/work-journey/export-pdf?layout=portrait'):
        response = work_journey_report_route.work_journey_report_pdf.__wrapped__(9)

    assert captured['template'] == 'modules/my_work/work_journey_report_print.html'
    assert response['company'].id == 9
    assert response['layout_mode'] == 'portrait'


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


def test_work_journey_source_urls_point_to_specific_origin_items():
    assert work_journey_sync.build_project_task_source_url(77, 501) == '/projects/77/manage?activity_id=501&from=work-journey'
    assert work_journey_sync.build_process_instance_source_url(9, 310) == '/my-work/process-instance/310?company_id=9&from=work-journey'
    assert work_journey_sync.build_meeting_source_url(9, 44) == '/meetings/company/9/meeting/44/report?from=work-journey'


def test_get_work_journey_board_excludes_completed_items(monkeypatch):
    employee = SimpleNamespace(id=3, weekly_hours=40, to_dict=lambda: {'id': 3, 'name': 'Ana'})
    anchor = date(2026, 4, 6)

    pending_item = SimpleNamespace(
        id=1,
        status='pending',
        due_date=anchor,
        occurrence_date=anchor,
        estimated_minutes=30,
        worked_minutes=0,
        priority='normal',
        title='Tarefa pendente',
        block_id=None,
    )
    completed_item = SimpleNamespace(
        id=2,
        status='completed',
        due_date=anchor,
        occurrence_date=anchor,
        estimated_minutes=45,
        worked_minutes=45,
        priority='normal',
        title='Tarefa concluída',
        block_id=None,
    )

    class _FakeBlockQueryAll:
        def filter_by(self, **_kwargs):
            return self

        def all(self):
            return []

    monkeypatch.setattr(work_journey_service, 'ensure_employee', lambda company_id, employee_id: employee)
    monkeypatch.setattr(work_journey_service, 'sync_work_journey_items', lambda company_id, employee_id, period_start, period_end: None)
    monkeypatch.setattr(work_journey_service, 'load_period_items', lambda company_id, employee_id, period_start, period_end: [pending_item, completed_item])
    monkeypatch.setattr(work_journey_service, 'suggest_blocks', lambda blocks, items, anchor_date: None)
    monkeypatch.setattr(work_journey_service, 'WorkJourneyBlock', SimpleNamespace(query=_FakeBlockQueryAll()))
    monkeypatch.setattr(work_journey_service, 'serialize_item', lambda item: {'id': item.id, 'status': item.status, 'title': item.title})

    payload = work_journey_service.get_work_journey_board(9, 3, anchor, 'week')

    assert [item['id'] for item in payload['period_items']] == [1]
    assert [item['id'] for item in payload['unassigned_items']] == [1]
    assert payload['summary']['pending_count'] == 1
    assert payload['summary']['completed_count'] == 0


def test_move_agenda_item_uses_persisted_entry_without_rebuilding(monkeypatch):
    employee = SimpleNamespace(id=3)
    agenda = SimpleNamespace(id=11, status='suggested', anchor_date=date(2026, 4, 6), scope='week')
    journey_item = SimpleNamespace(
        id=91,
        item_type='manual',
        due_date=date(2026, 4, 6),
        occurrence_date=date(2026, 4, 6),
    )
    entry = SimpleNamespace(
        id=55,
        company_id=9,
        employee_id=3,
        agenda_id=11,
        agenda=agenda,
        journey_item=journey_item,
        planned_date=date(2026, 4, 6),
        block_id=7,
        position_index=2,
        manual_override=False,
        updated_at=None,
    )
    commits = []
    captured = {}

    class _Session:
        def add(self, *_args, **_kwargs):
            return None

        def commit(self):
            commits.append('commit')

    monkeypatch.setattr(work_journey_agenda_service, 'ensure_employee', lambda company_id, employee_id: employee)
    monkeypatch.setattr(
        work_journey_agenda_service,
        'WorkJourneyAgendaItem',
        SimpleNamespace(query=_FakeAgendaMoveQuery(entry), journey_item=object(), agenda=object()),
    )
    monkeypatch.setattr(work_journey_agenda_service, 'joinedload', lambda value: value)
    monkeypatch.setattr(
        work_journey_agenda_service,
        '_get_or_build_agenda',
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('move não deve regenerar a agenda antes de localizar o item')),
    )
    monkeypatch.setattr(work_journey_agenda_service, 'shift_positions_before_insert', lambda *args, **kwargs: captured.setdefault('shift', args))
    monkeypatch.setattr(work_journey_agenda_service, 'apply_date_change_to_source', lambda item, target_date: captured.setdefault('target_date', target_date))
    monkeypatch.setattr(work_journey_agenda_service, 'recompute_agenda_summary', lambda agenda_obj: captured.setdefault('agenda_id', agenda_obj.id))
    monkeypatch.setattr(
        work_journey_agenda_service,
        '_serialize',
        lambda agenda_obj, employee_obj: {'agenda_id': agenda_obj.id, 'planned_date': entry.planned_date.isoformat()},
    )
    monkeypatch.setattr(work_journey_agenda_service, 'db', SimpleNamespace(session=_Session()))

    payload = work_journey_agenda_service.move_work_journey_agenda_item(
        9,
        3,
        date(2026, 4, 6),
        'week',
        55,
        {
            'target_date': date(2026, 4, 7),
            'block_id': None,
            'source_scope': 'overdue',
            'confirm_date_change': True,
            'position_index': 0,
        },
    )

    assert entry.planned_date == date(2026, 4, 7)
    assert entry.block_id is None
    assert entry.position_index == 0
    assert entry.manual_override is True
    assert entry.metadata_json['hide_from_overdue_lane'] is True
    assert captured['target_date'] == date(2026, 4, 7)
    assert captured['agenda_id'] == 11
    assert commits == ['commit', 'commit']
    assert payload['agenda_id'] == 11


def test_move_work_journey_agenda_item_accepts_target_block_id_alias(monkeypatch):
    employee = SimpleNamespace(id=3, company_id=9)
    agenda = SimpleNamespace(id=11, status='suggested')
    journey_item = SimpleNamespace(id=51, item_type='project_task')
    entry = SimpleNamespace(
        id=55,
        company_id=9,
        employee_id=3,
        agenda=agenda,
        journey_item=journey_item,
        journey_item_id=51,
        planned_date=date(2026, 4, 6),
        block_id=None,
        position_index=0,
        manual_override=False,
        metadata_json={},
        updated_at=None,
    )
    target_block = SimpleNamespace(id=88)
    commits = []
    captured = {}

    class _Session:
        def add(self, *_args, **_kwargs):
            return None

        def commit(self):
            commits.append('commit')

    monkeypatch.setattr(work_journey_agenda_service, 'ensure_employee', lambda company_id, employee_id: employee)
    monkeypatch.setattr(
        work_journey_agenda_service,
        'WorkJourneyAgendaItem',
        SimpleNamespace(query=_FakeAgendaMoveQuery(entry), journey_item=object(), agenda=object()),
    )
    monkeypatch.setattr(work_journey_agenda_service, 'joinedload', lambda value: value)
    def _fake_resolve_target_block(company_id, employee_id, target_date, item_type, block_id):
        captured['resolve'] = (company_id, employee_id, target_date, item_type, block_id)
        return target_block

    monkeypatch.setattr(work_journey_agenda_service, '_resolve_target_block', _fake_resolve_target_block)
    monkeypatch.setattr(work_journey_agenda_service, 'shift_positions_before_insert', lambda *args, **kwargs: captured.setdefault('shift', args))
    monkeypatch.setattr(work_journey_agenda_service, 'apply_date_change_to_source', lambda item, target_date: captured.setdefault('target_date', target_date))
    monkeypatch.setattr(work_journey_agenda_service, 'recompute_agenda_summary', lambda agenda_obj: captured.setdefault('agenda_id', agenda_obj.id))
    monkeypatch.setattr(
        work_journey_agenda_service,
        '_serialize',
        lambda agenda_obj, employee_obj: {'agenda_id': agenda_obj.id, 'planned_date': entry.planned_date.isoformat(), 'block_id': entry.block_id},
    )
    monkeypatch.setattr(work_journey_agenda_service, 'db', SimpleNamespace(session=_Session()))

    payload = work_journey_agenda_service.move_work_journey_agenda_item(
        9,
        3,
        date(2026, 4, 6),
        'week',
        55,
        {
            'target_date': date(2026, 4, 7),
            'target_block_id': 88,
            'source_scope': 'block',
            'confirm_date_change': True,
            'position_index': 0,
        },
    )

    assert captured['resolve'] == (9, 3, date(2026, 4, 7), 'project_task', 88)
    assert entry.planned_date == date(2026, 4, 7)
    assert entry.block_id == 88
    assert payload['block_id'] == 88
    assert commits == ['commit', 'commit']


def test_get_work_journey_agenda_persists_snapshot_before_serializing(monkeypatch):
    employee = SimpleNamespace(id=3, name='Ana')
    agenda = SimpleNamespace(id=11)
    commits = []

    class _Session:
        def commit(self):
            commits.append('commit')

    monkeypatch.setattr(work_journey_agenda_service, 'ensure_employee', lambda company_id, employee_id: employee)
    monkeypatch.setattr(work_journey_agenda_service, '_get_or_build_agenda', lambda *args, **kwargs: agenda)
    monkeypatch.setattr(work_journey_agenda_service, '_serialize', lambda agenda_obj, employee_obj: {'agenda_id': agenda_obj.id})
    monkeypatch.setattr(work_journey_agenda_service, 'db', SimpleNamespace(session=_Session()))

    payload = work_journey_agenda_service.get_work_journey_agenda(9, 3, date(2026, 4, 6), 'week', False)

    assert payload['agenda_id'] == 11
    assert commits == ['commit']


def test_generate_agenda_route_accepts_legacy_date_alias_without_extra_validation_error(monkeypatch):
    app = Flask(__name__)
    app.secret_key = 'test'
    captured = {}

    monkeypatch.setattr(work_journey_agendas_route, 'current_user', SimpleNamespace(id=7, is_authenticated=True))
    monkeypatch.setattr(work_journey_agendas_route, '_current_employee_id', lambda company_id: 3)
    monkeypatch.setattr(work_journey_agendas_route, '_can_manage_employee', lambda company_id, employee_id: True)
    monkeypatch.setattr(
        work_journey_agendas_route,
        'get_work_journey_agenda',
        lambda company_id, employee_id, anchor, scope, force: captured.update({
            'company_id': company_id,
            'employee_id': employee_id,
            'anchor': anchor,
            'scope': scope,
            'force': force,
        }) or {'id': 91},
    )
    monkeypatch.setattr(work_journey_agendas_route, 'WorkJourneyAgenda', SimpleNamespace(query=_FakeAgendaQuery()))

    with app.test_request_context(
        '/api/companies/9/work-journey/agendas/generate',
        method='POST',
        json={'employee_id': 3, 'date': '2026-04-06', 'scope': 'week'},
    ):
        response = work_journey_agendas_route.api_generate_agenda.__wrapped__(company_id=9)

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['success'] is True
    assert payload['data']['id'] == 91
    assert captured['anchor'] == date(2026, 4, 6)
    assert captured['scope'] == 'week'


def test_list_calendar_events_route_returns_service_payload(monkeypatch):
    app = Flask(__name__)
    app.secret_key = 'test'

    monkeypatch.setattr(work_journey_route, 'current_user', SimpleNamespace(id=7, is_authenticated=True))
    monkeypatch.setattr(work_journey_route, '_current_employee_id', lambda company_id: 3)
    monkeypatch.setattr(work_journey_route, '_can_access_employee', lambda company_id, employee_id: True)
    monkeypatch.setattr(
        work_journey_route,
        'list_calendar_events',
        lambda company_id, employee_id, **kwargs: [{'id': 10, 'title': 'Revisar contrato'}],
    )

    with app.test_request_context('/api/companies/9/work-journey/calendar/events?employee_id=3&start_date=2026-05-04&end_date=2026-05-10'):
        response = work_journey_route.api_list_calendar_events.__wrapped__(company_id=9)

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['success'] is True
    assert payload['data'][0]['title'] == 'Revisar contrato'


def test_create_calendar_event_route_parses_time_and_returns_event(monkeypatch):
    app = Flask(__name__)
    app.secret_key = 'test'

    monkeypatch.setattr(work_journey_route, 'current_user', SimpleNamespace(id=7, is_authenticated=True))
    monkeypatch.setattr(work_journey_route, '_can_manage_employee', lambda company_id, employee_id: True)
    monkeypatch.setattr(
        work_journey_route,
        'create_calendar_event',
        lambda company_id, payload, user_id: {
            'id': 11,
            'title': payload['title'],
            'start_time': payload['start_time'].strftime('%H:%M') if payload.get('start_time') else None,
            'block_id': payload.get('block_id'),
        },
    )

    with app.test_request_context(
        '/api/companies/9/work-journey/calendar/events',
        method='POST',
        json={
            'employee_id': 3,
            'title': 'Follow-up',
            'event_date': '2026-05-04',
            'start_time': '09:30',
            'block_id': 41,
            'source_type': 'manual',
        },
    ):
        response = work_journey_route.api_create_calendar_event.__wrapped__(company_id=9)

    http_response, status_code = response
    assert status_code == 201
    payload = http_response.get_json()
    assert payload['success'] is True
    assert payload['event']['start_time'] == '09:30'
    assert payload['event']['block_id'] == 41


def test_overdue_item_inside_current_week_starts_from_today_blocks(monkeypatch):
    monkeypatch.setattr(work_journey_agenda_engine, 'date', _AgendaCurrentWeekDate)
    monkeypatch.setattr(work_journey_agenda_engine, 'next_position_for_group', lambda *args, **kwargs: 0)

    sunday = date(2026, 4, 5)
    monday = date(2026, 4, 6)
    thursday = date(2026, 4, 9)
    friday = date(2026, 4, 10)
    agenda = SimpleNamespace(id=13, company_id=9, employee_id=3, anchor_date=thursday)
    item = SimpleNamespace(
        id=63,
        item_type='process_instance',
        block_id=None,
        status='pending',
        due_date=monday,
        occurrence_date=monday,
        estimated_minutes=180,
        metadata_json={},
    )
    monday_block = SimpleNamespace(
        id=301,
        block_mode='operational',
        accepted_item_types=['process_instance'],
        start_time=time(8, 0),
        end_time=time(9, 0),
    )
    thursday_block = SimpleNamespace(
        id=302,
        block_mode='operational',
        accepted_item_types=['process_instance'],
        start_time=time(8, 0),
        end_time=time(9, 0),
    )
    friday_block = SimpleNamespace(
        id=303,
        block_mode='operational',
        accepted_item_types=['process_instance'],
        start_time=time(8, 0),
        end_time=time(10, 0),
    )

    entries = work_journey_agenda_engine.allocate_item(
        item,
        agenda,
        {
            sunday: [],
            monday: [monday_block],
            date(2026, 4, 7): [],
            date(2026, 4, 8): [],
            thursday: [thursday_block],
            friday: [friday_block],
            date(2026, 4, 11): [],
        },
        defaultdict(int),
        sunday,
        date(2026, 4, 11),
    )

    assert [(entry.planned_date, entry.block_id, entry.allocated_minutes, entry.is_over_capacity, entry.overflow_minutes) for entry in entries] == [
        (friday, 303, 180, True, 60),
    ]


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
    with open(os.path.join(root, 'templates', 'modules', 'projects', 'project_task_v2.html'), 'r', encoding='utf-8') as handle:
        project_task_template = handle.read()
    with open(os.path.join(root, 'templates', 'modules', 'processes', 'process_instance_v2.html'), 'r', encoding='utf-8') as handle:
        process_instance_template = handle.read()

    assert 'Calendário Operacional do Colaborador' in journey_template
    assert 'work-journey-calendar-01.css' in journey_template
    assert 'journey-app--calendar01' in journey_template
    assert 'Calendário de:' in journey_template
    assert 'data-tab="agendas"' in journey_template
    assert 'work-journey-agendas.js' in journey_template
    assert 'work-journey-agendas-render.js' in journey_template
    assert journey_template.count("v='20260524-manual-events-actions-1'") == 3
    assert 'work-calendar-events.js' in journey_template
    assert 'journeySearchInput' in journey_template
    assert 'journeyApplyFiltersBtn' in journey_template
    assert 'journeyClearFiltersBtn' in journey_template
    assert 'journeyScopeSelect' not in journey_template
    assert journey_template.index('data-panel="manual-tasks"') < journey_template.index('id="journeyManualTaskForm"')
    assert 'journeyManualTaskForm' not in agendas_panel
    assert 'Planejamento operacional' in agendas_panel
    assert 'processInstanceCardsPanel' in agendas_panel
    assert 'processInstanceCardsList' in agendas_panel
    assert 'Evento operacional derivado' in agendas_panel or 'processInstanceCardsList' in agendas_panel
    assert 'calendarEventsList' in agendas_panel
    assert 'calendarEventBlockInput' in agendas_panel
    assert 'agendaBoardContainer' in agendas_panel
    assert 'A primeira coluna exibe eventos operacionais atrasados' in agendas_panel
    assert 'agendaSummaryCards' not in agendas_panel
    assert 'agendaMetaLine' not in agendas_panel
    assert 'agendaSearchStatus' not in agendas_panel
    assert 'Resumo visual do período' not in agendas_panel
    assert 'agendaLockBtn' in agendas_panel
    assert 'agendaPdfBtn' in agendas_panel
    assert 'agendaScopeSelect' not in agendas_panel
    assert 'agendaLockBadge' in agendas_panel
    assert '/calendar' in my_work_template
    assert 'Planejamento na Jornada' in routine_app32_template
    assert '/api/routines/${routineId}/journey-bindings' in routine_app32_template
    assert '/api/routines/${routineId}/journey-bindings' in routine_legacy_template
    assert 'Horas/Info' in project_task_template
    assert 'Horas/Info' in process_instance_template


def test_allocate_process_instance_respects_bound_block_preference(monkeypatch):
    monkeypatch.setattr(work_journey_agenda_engine, 'next_position_for_group', lambda *_args, **_kwargs: 0)

    target_day = date(2026, 4, 6)
    agenda = SimpleNamespace(id=13, company_id=9, employee_id=3, anchor_date=target_day)
    item = SimpleNamespace(
        id=64,
        item_type='process_instance',
        block_id=402,
        status='pending',
        due_date=target_day,
        occurrence_date=target_day,
        estimated_minutes=60,
        metadata_json={},
    )
    first_block = SimpleNamespace(
        id=401,
        block_mode='operational',
        accepted_item_types=['process_instance'],
        start_time=time(8, 0),
        end_time=time(9, 0),
    )
    preferred_block = SimpleNamespace(
        id=402,
        block_mode='operational',
        accepted_item_types=['process_instance'],
        start_time=time(9, 0),
        end_time=time(10, 0),
    )

    entries = work_journey_agenda_engine.allocate_item(
        item,
        agenda,
        {target_day: [first_block, preferred_block]},
        defaultdict(int),
        target_day,
        target_day,
    )

    assert len(entries) == 1
    assert entries[0].block_id == 402


def test_allocate_non_overdue_process_instance_into_next_compatible_future_block(monkeypatch):
    monkeypatch.setattr(work_journey_agenda_engine, 'next_position_for_group', lambda *_args, **_kwargs: 0)

    monday = date(2026, 4, 6)
    tuesday = date(2026, 4, 7)
    agenda = SimpleNamespace(id=21, company_id=9, employee_id=3, anchor_date=monday)
    item = SimpleNamespace(
        id=65,
        item_type='process_instance',
        block_id=None,
        status='pending',
        due_date=monday,
        occurrence_date=monday,
        estimated_minutes=90,
        metadata_json={},
    )
    tuesday_block = SimpleNamespace(
        id=501,
        block_mode='operational',
        accepted_item_types=['process_instance'],
        start_time=time(8, 0),
        end_time=time(10, 0),
    )

    entries = work_journey_agenda_engine.allocate_item(
        item,
        agenda,
        {
            monday: [],
            tuesday: [tuesday_block],
        },
        defaultdict(int),
        monday,
        tuesday,
    )

    assert [(entry.planned_date, entry.block_id, entry.allocated_minutes) for entry in entries] == [
        (tuesday, 501, 90),
    ]


def test_allocate_process_instance_into_buffer_block_when_it_accepts_type(monkeypatch):
    monkeypatch.setattr(work_journey_agenda_engine, 'next_position_for_group', lambda *_args, **_kwargs: 0)

    monday = date(2026, 4, 6)
    agenda = SimpleNamespace(id=23, company_id=9, employee_id=3, anchor_date=monday)
    item = SimpleNamespace(
        id=67,
        item_type='process_instance',
        block_id=None,
        status='pending',
        due_date=monday,
        occurrence_date=monday,
        estimated_minutes=60,
        metadata_json={},
    )
    buffer_block = SimpleNamespace(
        id=701,
        block_mode='buffer',
        accepted_item_types=['process_instance'],
        start_time=time(8, 0),
        end_time=time(9, 0),
    )

    entries = work_journey_agenda_engine.allocate_item(
        item,
        agenda,
        {monday: [buffer_block]},
        defaultdict(int),
        monday,
        monday,
    )

    assert [(entry.planned_date, entry.block_id, entry.allocated_minutes) for entry in entries] == [
        (monday, 701, 60),
    ]


def test_allocate_process_instance_respects_bound_block_preference_across_future_days(monkeypatch):
    monkeypatch.setattr(work_journey_agenda_engine, 'next_position_for_group', lambda *_args, **_kwargs: 0)

    monday = date(2026, 4, 6)
    tuesday = date(2026, 4, 7)
    wednesday = date(2026, 4, 8)
    agenda = SimpleNamespace(id=22, company_id=9, employee_id=3, anchor_date=monday)
    item = SimpleNamespace(
        id=66,
        item_type='process_instance',
        block_id=602,
        status='pending',
        due_date=monday,
        occurrence_date=monday,
        estimated_minutes=60,
        metadata_json={},
    )
    other_block = SimpleNamespace(
        id=601,
        block_mode='operational',
        accepted_item_types=['process_instance'],
        start_time=time(8, 0),
        end_time=time(9, 0),
    )
    preferred_block = SimpleNamespace(
        id=602,
        block_mode='operational',
        accepted_item_types=['process_instance'],
        start_time=time(9, 0),
        end_time=time(10, 0),
    )

    entries = work_journey_agenda_engine.allocate_item(
        item,
        agenda,
        {
            monday: [other_block],
            tuesday: [other_block],
            wednesday: [other_block, preferred_block],
        },
        defaultdict(int),
        monday,
        wednesday,
    )

    assert [(entry.planned_date, entry.block_id, entry.allocated_minutes) for entry in entries] == [
        (wednesday, 602, 60),
    ]


def test_allocate_item_keeps_single_card_when_no_block_has_full_capacity(monkeypatch):
    monkeypatch.setattr(work_journey_agenda_engine, 'next_position_for_group', lambda *_args, **_kwargs: 0)

    monday = date(2026, 4, 6)
    agenda = SimpleNamespace(id=24, company_id=9, employee_id=3, anchor_date=monday)
    item = SimpleNamespace(
        id=68,
        item_type='project_task',
        block_id=None,
        status='pending',
        due_date=monday,
        occurrence_date=monday,
        estimated_minutes=150,
        metadata_json={},
    )
    first_block = SimpleNamespace(
        id=801,
        block_mode='operational',
        accepted_item_types=['project_task'],
        start_time=time(8, 0),
        end_time=time(9, 0),
    )
    second_block = SimpleNamespace(
        id=802,
        block_mode='buffer',
        accepted_item_types=['project_task'],
        start_time=time(9, 0),
        end_time=time(10, 0),
    )

    entries = work_journey_agenda_engine.allocate_item(
        item,
        agenda,
        {monday: [first_block, second_block]},
        defaultdict(int),
        monday,
        monday,
    )

    assert len(entries) == 1
    assert entries[0].block_id == 801
    assert entries[0].allocated_minutes == 150
    assert entries[0].is_over_capacity is True
    assert entries[0].overflow_minutes == 90


def test_calendar_scripts_support_collaborator_without_employee_selector():
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    with open(os.path.join(root, 'static', 'js', 'work-journey.js'), 'r', encoding='utf-8') as handle:
        journey_script = handle.read()
    with open(os.path.join(root, 'static', 'js', 'work-calendar-events.js'), 'r', encoding='utf-8') as handle:
        calendar_events_script = handle.read()

    assert 'employeeSelect?.addEventListener' in journey_script
    assert 'parseManualTaskMinutes' in journey_script
    assert "formatValueByType('duration-minutes'" in journey_script
    assert "activateTab('manual-tasks')" in journey_script
    assert 'pythonWeekdayOfDate' in calendar_events_script
    assert '(current.getDay() + 6) % 7' in calendar_events_script


def test_agendas_script_supports_legacy_fallback_drag_and_drop():
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    with open(os.path.join(root, 'static', 'js', 'work-journey-agendas.js'), 'r', encoding='utf-8') as handle:
        agendas_script = handle.read()

    assert 'state.legacyFallback || !state.agenda?.id' in agendas_script
    assert '/work-journey/items/${source.item.id}' in agendas_script
    assert 'source.item.agenda_item_id || source.item.id' in agendas_script
    assert "return 'week';" in agendas_script


def test_agendas_scripts_support_drag_between_columns_and_blocks():
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    with open(os.path.join(root, 'static', 'js', 'work-journey-agendas.js'), 'r', encoding='utf-8') as handle:
        agendas_script = handle.read()
    with open(os.path.join(root, 'static', 'js', 'work-journey-agendas-render.js'), 'r', encoding='utf-8') as handle:
        render_script = handle.read()

    assert 'data-dropzone="block"' in render_script
    assert 'data-dropzone="day"' in render_script
    assert 'data-dropzone="unassigned"' in render_script
    assert 'data-list-scope="${listScope}"' in render_script
    assert 'source_scope: state.draggingScope || null' in agendas_script
    assert '/work-journey/agendas/items/' in agendas_script
    assert "state.agenda?.overdue_items || []" in agendas_script
    assert "state.agenda?.unassigned_items || []" in agendas_script
    assert 'data-dropzone="block" data-block-id="${blockId}"' in render_script


def test_agenda_manual_cards_expose_edit_and_complete_actions():
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    with open(os.path.join(root, 'static', 'js', 'work-journey-agendas.js'), 'r', encoding='utf-8') as handle:
        agendas_script = handle.read()
    with open(os.path.join(root, 'static', 'js', 'work-journey-agendas-render.js'), 'r', encoding='utf-8') as handle:
        render_script = handle.read()

    assert 'journey_item_id: item.journey_item_id || null' in render_script
    assert 'data-action="edit-manual-agenda-item"' in render_script
    assert 'data-action="complete-manual-agenda-item"' in render_script
    assert 'manualJourneyItemFromAction' in agendas_script
    assert '/work-journey/items/${item.id}' in agendas_script
    assert "body: JSON.stringify({ status: 'completed' })" in agendas_script
    assert 'openManualTaskForm?.(item)' in agendas_script


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
        is_overdue=False,
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
            is_overdue=True,
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
    assert payload['days'][0]['label'] == '05/04/2026'
    assert payload['days'][0]['subtitle'] == 'Dom'
    assert payload['summary']['overdue_count'] == 1
    monday_day = next(day for day in payload['days'] if day['date'] == '2026-04-06')
    assert monday_day['blocks'][0]['planned_minutes'] == 30
    assert monday_day['blocks'][1]['planned_minutes'] == 60
    assert monday_day['overdue_count'] == 1
    assert monday_day['overdue_items'][0]['id'] == 2
    assert monday_day['blocks'][1]['items'][0]['is_overdue'] is True
    assert payload['overdue_items'][0]['id'] == 2
    assert payload['unassigned_items'] == []


def test_agenda_presenter_includes_process_instance_cards(monkeypatch):
    monkeypatch.setattr(work_journey_agenda_presenter, 'build_item_display_code', lambda item: 'AA.IP.1')

    agenda = SimpleNamespace(
        id=7,
        company_id=9,
        employee_id=3,
        anchor_date=date(2026, 4, 6),
        scope='week',
        status='suggested',
        engine_version='agendas-v1',
        summary_json={},
    )
    employee = SimpleNamespace(name='Ana', to_dict=lambda: {'id': 3, 'name': 'Ana'})

    payload = work_journey_agenda_presenter.serialize_agenda_payload(
        agenda,
        employee,
        [],
        [],
        process_instance_cards=[
            {
                'instance_id': 501,
                'instance_title': 'Fechamento Fiscal Maio',
                'instance_due_label': '06/05/2026',
                'current_activity': {'activity_name': 'Conferir documentos'},
            }
        ],
    )

    assert payload['process_instance_cards'][0]['instance_id'] == 501
    assert payload['process_instance_cards'][0]['current_activity']['activity_name'] == 'Conferir documentos'


def test_process_instance_card_serialization_exposes_macro_and_current_activity(monkeypatch):
    monkeypatch.setattr(work_journey_agenda_service, 'date', _FixedDate)

    instance = SimpleNamespace(
        id=501,
        company_id=9,
        process_id=77,
        routine_id=44,
        instance_code='AA.IP.501',
        title='Fechamento Fiscal Maio',
        description='Rotina mensal do cliente',
        due_date=date(2026, 4, 6),
        status='in_progress',
        priority='high',
        current_bpmn_element_id='Task_ReviewDocs',
        process_rel=SimpleNamespace(name='Fiscal', code='PROC.FISCAL'),
        routine=SimpleNamespace(name='Fechamento mensal'),
    )
    execution = SimpleNamespace(
        id=88,
        process_instance_id=501,
        bpmn_element_id='Task_ReviewDocs',
        bpmn_element_name='Conferir documentos recebidos',
        bpmn_element_type='userTask',
        execution_mode='human_task',
        status='in_progress',
        waiting_since=None,
        started_at=datetime(2026, 4, 4, 9, 0),
        created_at=datetime(2026, 4, 4, 9, 0),
        metadata_json={'sla_minutes': 120},
    )
    related_item = SimpleNamespace(
        title='Conferir documentos recebidos',
        due_date=date(2026, 4, 4),
        status='ready',
        metadata_json={
            'source_url': '/companies/9/process-instances?instance_id=501&from=work-journey',
            'operational_due_label': '04/04/2026 11:00',
            'current_execution_id': 88,
        },
    )

    payload = work_journey_agenda_service._serialize_process_instance_card(
        instance,
        [execution],
        [related_item],
        agenda_entry_count=2,
        linked_event_count=1,
    )

    assert payload['instance_due_label'] == '06/04/2026'
    assert payload['current_activity']['activity_name'] == 'Conferir documentos recebidos'
    assert payload['current_activity']['activity_due_label'] == '04/04/2026 11:00'
    assert payload['agenda_entry_count'] == 2
    assert payload['linked_event_count'] == 1
    assert payload['linked_operational_task']['title'] == 'Conferir documentos recebidos'
    assert payload['linked_operational_task']['current_execution_id'] == 88


def test_process_execution_projection_prefers_active_human_task_due():
    instance = SimpleNamespace(
        title='Fechamento Fiscal Maio',
        description='Rotina mensal',
        due_date=date(2026, 4, 6),
        estimated_hours=5,
        actual_hours=1,
        worked_hours=1,
        current_bpmn_element_id='Task_ReviewDocs',
        status='in_progress',
    )
    execution = SimpleNamespace(
        id=88,
        bpmn_element_id='Task_ReviewDocs',
        bpmn_element_name='Conferir documentos recebidos',
        execution_mode='human_task',
        status='ready',
        estimated_hours=2,
        actual_hours=0.5,
        waiting_since=None,
        started_at=datetime(2026, 4, 4, 9, 0),
        created_at=datetime(2026, 4, 4, 9, 0),
        metadata_json={'sla_minutes': 120},
    )

    projection = process_execution_projection_service.build_operational_projection(instance, [execution])

    assert projection['operational_title'] == 'Conferir documentos recebidos'
    assert projection['operational_due_label'] == '04/04/2026 11:00'
    assert projection['estimated_minutes'] == 120
    assert projection['worked_minutes'] == 30
    assert projection['status'] == 'ready'


def test_agenda_presenter_separates_overdue_and_unassigned_items(monkeypatch):
    monkeypatch.setattr(work_journey_agenda_presenter, 'build_item_display_code', lambda item: 'AA.IP.1')
    monkeypatch.setattr(work_journey_agenda_presenter, 'date', _FixedDate)

    agenda = SimpleNamespace(
        id=2,
        company_id=9,
        employee_id=3,
        anchor_date=date(2026, 4, 6),
        scope='week',
        status='suggested',
        engine_version='agendas-v1',
        summary_json={},
    )
    employee = SimpleNamespace(name='Ana', to_dict=lambda: {'id': 3, 'name': 'Ana'})
    monday_block = SimpleNamespace(
        id=10,
        name='Operacional',
        description='Bloco operacional',
        start_time=time(8, 0),
        end_time=time(9, 0),
        block_mode='operational',
        weekdays_json=[0],
    )
    overdue_item = SimpleNamespace(
        id=31,
        company_id=9,
        item_type='manual',
        source_id=None,
        title='Tarefa atrasada',
        description='',
        status='pending',
        priority='normal',
        due_date=date(2026, 4, 3),
        occurrence_date=date(2026, 4, 3),
        is_overdue=True,
        worked_minutes=0,
        estimated_minutes=15,
        metadata_json={},
        block=None,
    )
    unassigned_item = SimpleNamespace(
        id=32,
        company_id=9,
        item_type='manual',
        source_id=None,
        title='Tarefa sem alocação',
        description='',
        status='pending',
        priority='normal',
        due_date=date(2026, 4, 6),
        occurrence_date=date(2026, 4, 6),
        is_overdue=False,
        worked_minutes=0,
        estimated_minutes=20,
        metadata_json={},
        block=None,
    )
    overdue_entry = SimpleNamespace(
        id=3,
        agenda_id=2,
        company_id=9,
        employee_id=3,
        journey_item_id=31,
        block_id=10,
        planned_date=date(2026, 4, 6),
        position_index=0,
        allocated_minutes=15,
        planned_start_minutes=480,
        planned_end_minutes=495,
        overflow_minutes=0,
        is_fixed=False,
        is_over_capacity=False,
        manual_override=False,
        metadata_json={},
        block=monday_block,
        journey_item=overdue_item,
    )
    unassigned_entry = SimpleNamespace(
        id=4,
        agenda_id=2,
        company_id=9,
        employee_id=3,
        journey_item_id=32,
        block_id=None,
        planned_date=date(2026, 4, 6),
        position_index=1,
        allocated_minutes=20,
        planned_start_minutes=None,
        planned_end_minutes=None,
        overflow_minutes=0,
        is_fixed=False,
        is_over_capacity=False,
        manual_override=False,
        metadata_json={},
        block=None,
        journey_item=unassigned_item,
    )

    payload = work_journey_agenda_presenter.serialize_agenda_payload(
        agenda,
        employee,
        [monday_block],
        [overdue_entry, unassigned_entry],
    )

    monday_day = next(day for day in payload['days'] if day['date'] == '2026-04-06')

    assert payload['overdue_items'][0]['id'] == 3
    assert payload['unassigned_items'][0]['id'] == 4
    assert monday_day['overdue_items'][0]['id'] == 3
    assert monday_day['unassigned_items'][0]['id'] == 4
    assert payload['summary']['overdue_count'] == 1


def test_agenda_presenter_marks_item_overdue_from_due_date_without_explicit_flag(monkeypatch):
    monkeypatch.setattr(work_journey_agenda_presenter, 'build_item_display_code', lambda item: 'AA.V.99')
    monkeypatch.setattr(work_journey_agenda_presenter, 'date', _FixedDate)

    overdue_item = SimpleNamespace(
        id=99,
        company_id=9,
        item_type='manual',
        source_id=None,
        title='Tarefa vencida',
        description='',
        status='pending',
        priority='normal',
        due_date=_FixedDate(2026, 4, 3),
        occurrence_date=_FixedDate(2026, 4, 3),
        worked_minutes=0,
        estimated_minutes=30,
        metadata_json={},
        block=None,
    )
    entry = SimpleNamespace(
        id=9,
        agenda_id=2,
        company_id=9,
        employee_id=3,
        journey_item_id=99,
        block_id=None,
        planned_date=_FixedDate(2026, 4, 5),
        position_index=0,
        allocated_minutes=30,
        planned_start_minutes=None,
        planned_end_minutes=None,
        overflow_minutes=0,
        is_fixed=False,
        is_over_capacity=False,
        manual_override=False,
        metadata_json={},
        block=None,
        journey_item=overdue_item,
    )

    payload = work_journey_agenda_presenter.serialize_agenda_entry(entry)

    assert payload['is_overdue'] is True


def test_agenda_presenter_excludes_completed_entries_from_payload(monkeypatch):
    monkeypatch.setattr(work_journey_agenda_presenter, 'build_item_display_code', lambda item: f'AA.T.{item.id}')

    agenda = SimpleNamespace(
        id=3,
        company_id=9,
        employee_id=3,
        anchor_date=date(2026, 4, 6),
        scope='week',
        status='suggested',
        engine_version='agendas-v1',
        summary_json={},
    )
    employee = SimpleNamespace(name='Ana', to_dict=lambda: {'id': 3, 'name': 'Ana'})
    block = SimpleNamespace(
        id=10,
        name='Operacional',
        description='Bloco operacional',
        start_time=time(8, 0),
        end_time=time(9, 0),
        block_mode='operational',
        weekdays_json=[0],
    )
    pending_item = SimpleNamespace(
        id=41,
        company_id=9,
        item_type='manual',
        source_id=None,
        title='Tarefa ativa',
        description='',
        status='pending',
        priority='normal',
        due_date=date(2026, 4, 6),
        occurrence_date=date(2026, 4, 6),
        worked_minutes=0,
        estimated_minutes=30,
        metadata_json={},
        block=None,
    )
    completed_item = SimpleNamespace(
        id=42,
        company_id=9,
        item_type='manual',
        source_id=None,
        title='Tarefa concluída',
        description='',
        status='completed',
        priority='normal',
        due_date=date(2026, 4, 6),
        occurrence_date=date(2026, 4, 6),
        worked_minutes=30,
        estimated_minutes=30,
        metadata_json={},
        block=None,
    )
    pending_entry = SimpleNamespace(
        id=5,
        agenda_id=3,
        company_id=9,
        employee_id=3,
        journey_item_id=41,
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
        block=block,
        journey_item=pending_item,
    )
    completed_entry = SimpleNamespace(
        id=6,
        agenda_id=3,
        company_id=9,
        employee_id=3,
        journey_item_id=42,
        block_id=10,
        planned_date=date(2026, 4, 6),
        position_index=1,
        allocated_minutes=30,
        planned_start_minutes=510,
        planned_end_minutes=540,
        overflow_minutes=0,
        is_fixed=False,
        is_over_capacity=False,
        manual_override=False,
        metadata_json={},
        block=block,
        journey_item=completed_item,
    )

    payload = work_journey_agenda_presenter.serialize_agenda_payload(
        agenda,
        employee,
        [block],
        [pending_entry, completed_entry],
    )

    monday_day = next(day for day in payload['days'] if day['date'] == '2026-04-06')

    assert [item['journey_item_id'] for item in monday_day['blocks'][0]['items']] == [41]
    assert payload['summary']['pending_count'] == 1
    assert payload['summary']['completed_count'] == 0


def test_agenda_presenter_hides_manually_reprogrammed_overdue_item_from_side_lane(monkeypatch):
    monkeypatch.setattr(work_journey_agenda_presenter, 'build_item_display_code', lambda item: f'AA.T.{item.id}')
    monkeypatch.setattr(work_journey_agenda_presenter, 'date', _FixedDate)

    agenda = SimpleNamespace(
        id=4,
        company_id=9,
        employee_id=3,
        anchor_date=date(2026, 4, 6),
        scope='week',
        status='suggested',
        engine_version='agendas-v1',
        summary_json={},
    )
    employee = SimpleNamespace(name='Ana', to_dict=lambda: {'id': 3, 'name': 'Ana'})
    block = SimpleNamespace(
        id=10,
        name='Operacional',
        description='Bloco operacional',
        start_time=time(8, 0),
        end_time=time(9, 0),
        block_mode='operational',
        weekdays_json=[0],
    )
    overdue_item = SimpleNamespace(
        id=51,
        company_id=9,
        item_type='manual',
        source_id=None,
        title='Tarefa reprogramada',
        description='',
        status='pending',
        priority='normal',
        due_date=_FixedDate(2026, 4, 3),
        occurrence_date=_FixedDate(2026, 4, 3),
        worked_minutes=0,
        estimated_minutes=30,
        metadata_json={},
        block=None,
    )
    entry = SimpleNamespace(
        id=7,
        agenda_id=4,
        company_id=9,
        employee_id=3,
        journey_item_id=51,
        block_id=10,
        planned_date=_FixedDate(2026, 4, 6),
        position_index=0,
        allocated_minutes=30,
        planned_start_minutes=480,
        planned_end_minutes=510,
        overflow_minutes=0,
        is_fixed=False,
        is_over_capacity=False,
        manual_override=True,
        metadata_json={'hide_from_overdue_lane': True},
        block=block,
        journey_item=overdue_item,
    )

    payload = work_journey_agenda_presenter.serialize_agenda_payload(
        agenda,
        employee,
        [block],
        [entry],
    )

    monday_day = next(day for day in payload['days'] if day['date'] == '2026-04-06')

    assert payload['overdue_items'] == []
    assert monday_day['blocks'][0]['items'][0]['journey_item_id'] == 51
    assert monday_day['blocks'][0]['items'][0]['is_overdue'] is True


def test_agenda_presenter_includes_calendar_events_inside_blocks(monkeypatch):
    monkeypatch.setattr(work_journey_agenda_presenter, 'build_item_display_code', lambda item: f'AA.T.{item.id}')

    agenda = SimpleNamespace(
        id=5,
        company_id=9,
        employee_id=3,
        anchor_date=date(2026, 4, 6),
        scope='week',
        status='suggested',
        engine_version='agendas-v1',
        summary_json={},
    )
    employee = SimpleNamespace(name='Ana', to_dict=lambda: {'id': 3, 'name': 'Ana'})
    block = SimpleNamespace(
        id=10,
        name='Operacional',
        description='Bloco operacional',
        start_time=time(8, 0),
        end_time=time(10, 0),
        block_mode='operational',
        weekdays_json=[0],
    )
    task_item = SimpleNamespace(
        id=61,
        company_id=9,
        item_type='manual',
        source_id=None,
        title='Tarefa ativa',
        description='',
        status='pending',
        priority='normal',
        due_date=date(2026, 4, 6),
        occurrence_date=date(2026, 4, 6),
        worked_minutes=30,
        estimated_minutes=30,
        metadata_json={},
        block=None,
    )
    task_entry = SimpleNamespace(
        id=8,
        agenda_id=5,
        company_id=9,
        employee_id=3,
        journey_item_id=61,
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
        block=block,
        journey_item=task_item,
    )
    calendar_event = SimpleNamespace(
        id=99,
        company_id=9,
        employee_id=3,
        block_id=10,
        source_type='process_instance',
        source_id=501,
        title='Revisar instância',
        description='Follow-up operacional',
        event_date=date(2026, 4, 6),
        start_time=time(9, 0),
        end_time=time(9, 30),
        status='confirmed',
        priority='high',
        execution_notes='Lembrar de lançar horas',
        metadata_json={
            'source_url': '/companies/9/process-instances?instance_id=501',
            'source_code': 'IP.501',
            'source_title': 'Fechamento mensal',
        },
        block=block,
        employee=SimpleNamespace(name='Ana'),
    )

    payload = work_journey_agenda_presenter.serialize_agenda_payload(
        agenda,
        employee,
        [block],
        [task_entry],
        [calendar_event],
    )

    monday_day = next(day for day in payload['days'] if day['date'] == '2026-04-06')
    monday_block = monday_day['blocks'][0]

    assert monday_block['planned_task_minutes'] == 30
    assert monday_block['planned_event_minutes'] == 30
    assert monday_block['planned_minutes'] == 60
    assert monday_block['events'][0]['event_id'] == 99
    assert monday_block['events'][0]['item_kind'] == 'calendar_event'
    assert payload['summary']['event_count'] == 1
    assert payload['summary']['linked_event_count'] == 1


def test_work_journey_report_page_renders_management_report(monkeypatch):
    app = Flask(__name__)
    app.secret_key = 'test'
    app.add_url_rule(
        '/companies/<int:company_id>/work-journey/export-pdf',
        endpoint='work_journey_report.work_journey_report_pdf',
        view_func=lambda company_id: f'pdf-{company_id}',
    )
    company = SimpleNamespace(id=9, name='Empresa Teste')
    captured = {}

    monkeypatch.setattr(work_journey_report_route, 'Company', SimpleNamespace(query=_FakeCompanyQuery(company)))
    monkeypatch.setattr(work_journey_report_route, 'has_company_full_access', lambda company_id: True)
    monkeypatch.setattr(work_journey_report_route, 'build_work_journey_management_report', lambda *args, **kwargs: {'summary': {'scope_label': 'Empresa inteira'}, 'filters': {'department': None, 'employee_id': None, 'employees': [], 'departments': []}, 'period': {'week_label': '06/04 a 12/04', 'month_label': '04/2026'}, 'anchor_date': '2026-04-06', 'charts': {'scope_capacity': {'labels': [], 'values': []}, 'scope_mix': {'labels': [], 'values': []}, 'employees_capacity': {'labels': [], 'occupied': [], 'free': []}, 'blocks_capacity': {'labels': [], 'occupied': [], 'free': []}}, 'employees': []})
    monkeypatch.setattr(work_journey_report_route, 'render_template', lambda template, **ctx: captured.update({'template': template, 'ctx': ctx}) or ctx)

    with app.test_request_context('/companies/9/work-journey/report'):
        response = work_journey_report_route.work_journey_report_page.__wrapped__(company_id=9)

    assert captured['template'] == 'modules/my_work/work_journey_report.html'
    assert response['report']['summary']['scope_label'] == 'Empresa inteira'



def test_work_journey_template_exposes_report_link():
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    with open(os.path.join(root, 'templates', 'modules', 'my_work', 'work_journey.html'), 'r', encoding='utf-8') as handle:
        template = handle.read()
    assert 'Relatório gerencial' in template
    assert 'work_journey_report.work_journey_report_page' in template


def test_sync_process_instance_item_materializes_operational_task(monkeypatch):
    instance = SimpleNamespace(
        id=501,
        company_id=9,
        process_id=41,
        routine_id=12,
        instance_code='IP.501',
        title='Fechamento Fiscal Maio',
        description='Rotina mensal',
        due_date=date(2026, 5, 5),
        priority='high',
        status='in_progress',
        process_rel=SimpleNamespace(name='Fechamento Fiscal', code='AA.P.1'),
        routine=SimpleNamespace(schedule_type='monthly'),
    )
    execution = SimpleNamespace(id=88, bpmn_element_id='Task_1', bpmn_element_name='Conferir documentos')
    captured = {}

    class _FakeProcessInstanceSingleQuery:
        def options(self, *_args, **_kwargs):
            return self
        def filter(self, *_args, **_kwargs):
            return self
        def first(self):
            return instance

    class _FakeExecutionSingleQuery:
        def filter(self, *_args, **_kwargs):
            return self
        def order_by(self, *_args, **_kwargs):
            return self
        def all(self):
            return [execution]

    class _FakeJourneyItemLookup:
        def filter_by(self, **kwargs):
            self.kwargs = kwargs
            return self
        def first(self):
            return SimpleNamespace(id=901, employee_id=3) if self.kwargs.get('source_id') == 501 else None

    monkeypatch.setattr(work_journey_sync, 'ProcessInstance', SimpleNamespace(query=_FakeProcessInstanceSingleQuery(), process_rel=None, routine=None, company_id=None, id=None))
    sort_column = SimpleNamespace(desc=lambda: sort_column)
    monkeypatch.setattr(
        work_journey_sync,
        'ProcessInstanceExecution',
        SimpleNamespace(query=_FakeExecutionSingleQuery(), company_id=None, process_instance_id=None, updated_at=sort_column, id=sort_column),
    )
    monkeypatch.setattr(work_journey_sync, 'WorkJourneyItem', SimpleNamespace(query=_FakeJourneyItemLookup()))
    monkeypatch.setattr(work_journey_sync, 'joinedload', lambda attr: attr)
    monkeypatch.setattr(
        work_journey_sync,
        'build_operational_projection',
        lambda *_args, **_kwargs: {
            'current_execution': execution,
            'operational_title': 'Conferir documentos',
            'operational_description': 'Fechamento Fiscal Maio',
            'operational_due_date': date(2026, 5, 5),
            'operational_due_label': '05/05/2026',
            'estimated_minutes': 90,
            'worked_minutes': 15,
            'status': 'ready',
            'activity_due_at': '2026-05-05T10:00:00',
            'activity_due_date': '2026-05-05',
            'is_activity_overdue': False,
        },
    )
    monkeypatch.setattr(work_journey_sync, '_resolve_process_instance_employee_id', lambda *_args, **_kwargs: 3)
    monkeypatch.setattr(work_journey_sync, 'get_bound_block_id', lambda *_args, **_kwargs: 21)
    monkeypatch.setattr(work_journey_sync, 'current_manual_assignment', lambda *_args, **_kwargs: False)
    monkeypatch.setattr(work_journey_sync, 'upsert_source_item', lambda **kwargs: captured.update(kwargs))

    item = work_journey_sync.sync_process_instance_item(9, 501, preferred_employee_id=3)

    assert item.id == 901
    assert captured['employee_id'] == 3
    assert captured['item_type'] == 'process_instance'
    assert captured['title'] == 'Conferir documentos'
    assert captured['estimated_minutes'] == 90
    assert captured['bound_block_id'] == 21
    assert captured['metadata']['current_execution_id'] == 88


def test_sync_meeting_item_materializes_operational_task(monkeypatch):
    meeting = SimpleNamespace(
        id=77,
        company_id=9,
        project_id=15,
        title='Reunião de alinhamento',
        invite_notes='Alinhar pendências',
        meeting_notes='Notas finais',
        scheduled_date=date(2026, 5, 5),
        scheduled_time='09:00',
        planned_duration_minutes=45,
        actual_duration_minutes=30,
        status='draft',
        company=SimpleNamespace(client_code='AA'),
    )
    captured = {}

    class _FakeMeetingQuery:
        def filter_by(self, **_kwargs):
            return self
        def first(self):
            return meeting

    class _FakeJourneyItemLookup:
        def filter_by(self, **kwargs):
            self.kwargs = kwargs
            return self
        def first(self):
            return SimpleNamespace(id=902, employee_id=3) if self.kwargs.get('source_id') == 77 else None

    monkeypatch.setattr(work_journey_sync, 'Meeting', SimpleNamespace(query=_FakeMeetingQuery()))
    monkeypatch.setattr(work_journey_sync, 'WorkJourneyItem', SimpleNamespace(query=_FakeJourneyItemLookup()))
    monkeypatch.setattr(work_journey_sync, '_resolve_meeting_employee_id', lambda *_args, **_kwargs: 3)
    monkeypatch.setattr(work_journey_sync, 'current_manual_assignment', lambda *_args, **_kwargs: False)
    monkeypatch.setattr(work_journey_sync, 'upsert_source_item', lambda **kwargs: captured.update(kwargs))

    item = work_journey_sync.sync_meeting_item(9, 77, preferred_employee_id=3)

    assert item.id == 902
    assert captured['employee_id'] == 3
    assert captured['item_type'] == 'meeting'
    assert captured['title'] == 'Reunião de alinhamento'
    assert captured['estimated_minutes'] == 45
    assert captured['metadata']['source_label'] == 'Reunião'


def test_propagate_item_status_updates_human_process_execution(monkeypatch):
    now = datetime(2026, 5, 5, 12, 0, 0)
    instance = SimpleNamespace(id=501, current_bpmn_element_id=None, actual_hours=0, worked_hours=0, completed_at=None, status='pending')
    execution = SimpleNamespace(
        id=88,
        company_id=9,
        execution_mode='human_task',
        status='ready',
        started_at=None,
        completed_at=None,
        paused_at=None,
        waiting_since=None,
        duration_seconds=None,
        actual_hours=0,
        bpmn_element_id='Task_1',
    )

    class _FakeInstanceQuery:
        @staticmethod
        def get(source_id):
            return instance if source_id == 501 else None

    class _FakeExecutionQuery:
        @staticmethod
        def get(execution_id):
            return execution if execution_id == 88 else None

    added = []

    monkeypatch.setattr(work_journey_sync, 'ProcessInstance', SimpleNamespace(query=_FakeInstanceQuery()))
    monkeypatch.setattr(work_journey_sync, 'ProcessInstanceExecution', SimpleNamespace(query=_FakeExecutionQuery()))
    monkeypatch.setattr(work_journey_sync, 'datetime', SimpleNamespace(utcnow=lambda: now))
    monkeypatch.setattr(work_journey_sync.db, 'session', SimpleNamespace(add=lambda obj: added.append(obj)))

    item = SimpleNamespace(
        item_type='process_instance',
        source_id=501,
        company_id=9,
        status='completed',
        worked_minutes=90,
        metadata_json={'current_execution_id': 88},
    )

    work_journey_sync.propagate_item_status(item)

    assert instance.status == 'completed'
    assert instance.actual_hours == 1.5
    assert instance.completed_at == now
    assert instance.current_bpmn_element_id == 'Task_1'
    assert execution.status == 'completed'
    assert execution.started_at == now
    assert execution.completed_at == now
    assert execution.duration_seconds == 0
    assert execution.actual_hours == 1.5
    assert added == [instance, execution]


def test_update_work_item_resyncs_process_instance_projection(monkeypatch):
    item = SimpleNamespace(
        id=91,
        company_id=9,
        employee_id=3,
        item_type='process_instance',
        source_id=501,
        status='pending',
        completed_at=None,
        updated_at=None,
        worked_minutes=0,
        metadata_json={},
    )
    synced_item = SimpleNamespace(id=92)
    captured = {}

    class _FakeItemQuery:
        def filter_by(self, **kwargs):
            self.kwargs = kwargs
            return self
        def first(self):
            return item if self.kwargs.get('id') == 91 else None

    monkeypatch.setattr(work_journey_service, 'WorkJourneyItem', SimpleNamespace(query=_FakeItemQuery()))
    monkeypatch.setattr(work_journey_service, 'serialize_item', lambda current: {'id': current.id})
    monkeypatch.setattr(work_journey_service, 'propagate_item_status', lambda current: captured.setdefault('propagated_status', current.status))
    monkeypatch.setattr(
        work_journey_service,
        'sync_process_instance_item',
        lambda company_id, source_id, preferred_employee_id=None: captured.update(
            {'company_id': company_id, 'source_id': source_id, 'preferred_employee_id': preferred_employee_id}
        ) or synced_item,
    )
    monkeypatch.setattr(work_journey_service, 'sync_meeting_item', lambda *args, **kwargs: None)
    monkeypatch.setattr(
        work_journey_service.db,
        'session',
        SimpleNamespace(add=lambda *_args, **_kwargs: None, commit=lambda: captured.setdefault('commit_count', 0) or captured.update({'commit_count': captured.get('commit_count', 0) + 1})),
    )
    monkeypatch.setattr(work_journey_service, 'datetime', SimpleNamespace(utcnow=lambda: datetime(2026, 5, 5, 12, 0, 0)))

    payload = {'status': 'completed', 'worked_minutes': 60}
    response = work_journey_service.update_work_item(9, 91, payload)

    assert response == {'id': 92}
    assert captured['propagated_status'] == 'completed'
    assert captured['company_id'] == 9
    assert captured['source_id'] == 501
    assert captured['preferred_employee_id'] == 3


def test_process_resource_sync_helper_prefers_current_user_employee(monkeypatch):
    captured = {}

    monkeypatch.setattr(
        process_resource,
        'Employee',
        SimpleNamespace(query=SimpleNamespace(filter_by=lambda **_kwargs: SimpleNamespace(first=lambda: SimpleNamespace(id=31)))),
    )
    monkeypatch.setattr(process_resource, 'current_user', SimpleNamespace(id=7))
    monkeypatch.setattr(
        process_resource,
        'sync_process_instance_item',
        lambda company_id, instance_id, preferred_employee_id=None: captured.update(
            {'company_id': company_id, 'instance_id': instance_id, 'preferred_employee_id': preferred_employee_id}
        ),
    )
    monkeypatch.setattr(process_resource.db, 'session', SimpleNamespace(commit=lambda: captured.update({'committed': True})))

    process_resource._sync_process_instance_work_journey_item(SimpleNamespace(id=501, company_id=9))

    assert captured == {'company_id': 9, 'instance_id': 501, 'preferred_employee_id': 31, 'committed': True}


def test_meeting_resource_sync_helper_prefers_current_user_employee(monkeypatch):
    captured = {}

    monkeypatch.setattr(
        meeting_resource,
        'Employee',
        SimpleNamespace(query=SimpleNamespace(filter_by=lambda **_kwargs: SimpleNamespace(first=lambda: SimpleNamespace(id=44)))),
    )
    monkeypatch.setattr(meeting_resource, 'current_user', SimpleNamespace(id=9))
    monkeypatch.setattr(
        meeting_resource,
        'sync_meeting_item',
        lambda company_id, meeting_id, preferred_employee_id=None: captured.update(
            {'company_id': company_id, 'meeting_id': meeting_id, 'preferred_employee_id': preferred_employee_id}
        ),
    )
    monkeypatch.setattr(meeting_resource.db, 'session', SimpleNamespace(commit=lambda: captured.update({'committed': True})))

    meeting_resource._sync_meeting_work_journey_item(SimpleNamespace(id=77, company_id=9))

    assert captured == {'company_id': 9, 'meeting_id': 77, 'preferred_employee_id': 44, 'committed': True}

