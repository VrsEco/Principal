import os
import sys
import json
from types import SimpleNamespace

from flask import Flask

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api.resources import meeting as meeting_resource
import models


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
    def __init__(self, employee=None, employees=None):
        self.employee = employee
        self.employees = employees or []
        self.last_filter_kwargs = None

    def filter_by(self, **kwargs):
        self.last_filter_kwargs = kwargs
        return self

    def first(self):
        return self.employee

    def all(self):
        return self.employees


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


class _FakeListQuery:
    def __init__(self, items=None):
        self.items = items or []
        self.last_filter_kwargs = None

    def filter_by(self, **kwargs):
        self.last_filter_kwargs = kwargs
        return self

    def all(self):
        return self.items


class _FakeFilterAllQuery:
    def __init__(self, items=None):
        self.items = items or []
        self.filtered = False

    def filter(self, *args, **kwargs):
        self.filtered = True
        return self

    def all(self):
        return self.items


class _FakeDbSession:
    def __init__(self):
        self.added = []
        self.committed = 0
        self.rolled_back = False

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.committed += 1

    def rollback(self):
        self.rolled_back = True


class _FakeColumn:
    def in_(self, values):
        return values


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


def test_meeting_create_rejects_blank_title(monkeypatch):
    app = _build_app()
    monkeypatch.setattr(meeting_resource, 'user_can_access_company', lambda company_id: True)

    with app.test_request_context('/meetings/api/company/12/meeting', method='POST', json={'title': '   '}):
        response, status = meeting_resource.MeetingListResource().post.__wrapped__(
            meeting_resource.MeetingListResource(), 12
        )

    assert status == 400
    assert response['success'] is False
    assert response['message'] == 'Informe o título da reunião.'


def test_meeting_create_persists_trimmed_title_without_schedule(monkeypatch):
    app = _build_app()
    captured = {}
    fake_session = _FakeDbSession()

    class _FakeMeeting:
        def __init__(self, **kwargs):
            captured.update(kwargs)
            self.id = 77
            self.updated_at = None

    monkeypatch.setattr(meeting_resource, 'user_can_access_company', lambda company_id: True)
    monkeypatch.setattr(meeting_resource, 'Meeting', _FakeMeeting)
    monkeypatch.setattr(meeting_resource.db, 'session', fake_session)
    monkeypatch.setattr(meeting_resource, '_sync_meeting_work_journey_item', lambda meeting: None)

    with app.test_request_context(
        '/meetings/api/company/12/meeting',
        method='POST',
        json={'title': '  Comitê Executivo  '},
    ):
        response, status = meeting_resource.MeetingListResource().post.__wrapped__(
            meeting_resource.MeetingListResource(), 12
        )

    assert status == 201
    assert response['success'] is True
    assert response['meeting_id'] == 77
    assert captured['company_id'] == 12
    assert captured['title'] == 'Comitê Executivo'
    assert captured['scheduled_date'] is None
    assert fake_session.committed == 1


def test_meetings_template_contains_delete_action():
    template_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'templates', 'meetings_manage.html'))
    with open(template_path, 'r', encoding='utf-8') as handle:
        content = handle.read()

    assert 'btn-excluir-reuniao-editor' in content
    assert 'window.excluirReuniao = excluirReuniao;' in content
    assert "method: 'DELETE'" in content
    assert 'data-meeting-id="{{ meeting.id }}"' in content
    assert 'data-meeting-title="{{ meeting.title|e }}"' in content
    assert 'excluirReuniao(Number(this.dataset.meetingId), this.dataset.meetingTitle)' in content
    assert 'excluirReuniao({{ meeting.id }}, {{ meeting.title|tojson|safe }})' not in content


def test_meetings_template_uses_execucao_endpoint_without_accent():
    template_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'templates', 'meetings_manage.html'))
    with open(template_path, 'r', encoding='utf-8') as handle:
        content = handle.read()

    assert '/execucao?company_id=${meetingsCompanyId}' in content
    assert '/execucação?company_id=${meetingsCompanyId}' not in content


def test_meetings_template_can_create_activity_from_discussion():
    template_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'templates', 'meetings_manage.html'))
    with open(template_path, 'r', encoding='utf-8') as handle:
        content = handle.read()

    assert 'function criarAtividadeDaDiscussao(index)' in content
    assert 'source_discussion_title' in content
    assert '+ Gerar atividade' in content


def test_meetings_template_keeps_finalize_button_and_timezone_label():
    template_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'templates', 'meetings_manage.html'))
    with open(template_path, 'r', encoding='utf-8') as handle:
        content = handle.read()

    assert 'btn-finalizar-reuniao-quick' in content
    assert 'America/Bahia' in content
    assert 'Salvar e Definir Atividades' not in content
    assert 'Salvar e focar plano de ação' not in content


def test_meetings_template_has_activity_edit_delete_save_cancel_flow():
    template_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'templates', 'meetings_manage.html'))
    with open(template_path, 'r', encoding='utf-8') as handle:
        content = handle.read()

    assert 'function iniciarEdicaoAtividade(index)' in content
    assert 'function salvarAtividade(index)' in content
    assert 'function cancelarEdicaoAtividade(index)' in content
    assert '>Editar</button>' in content
    assert '>Excluir</button>' in content
    assert '>Cancelar</button>' in content
    assert '>Salvar atividade</button>' in content
    assert 'getPersistableActivities()' in content


def test_meetings_template_has_summary_share_actions():
    template_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'templates', 'meetings_manage.html'))
    with open(template_path, 'r', encoding='utf-8') as handle:
        content = handle.read()

    assert 'btn-enviar-resumo-editor' in content
    assert 'meeting-share-summary-modal' in content
    assert 'function carregarDestinatariosResumoReuniao(meetingId)' in content
    assert '/summary-recipients?company_id=${meetingsCompanyId}' in content
    assert '/share-summary?company_id=${meetingsCompanyId}' in content


def test_meetings_template_shows_discussion_and_activity_counts_on_cards():
    template_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'templates', 'meetings_manage.html'))
    with open(template_path, 'r', encoding='utf-8') as handle:
        content = handle.read()

    assert '{% set discussions_count = meeting.discussions | length if meeting.discussions else 0 %}' in content
    assert '{% set activities_count = meeting.activities | length if meeting.activities else 0 %}' in content
    assert '<strong>Decis&otilde;es:</strong>' in content
    assert '<strong>Atividades:</strong>' in content


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


def test_meeting_summary_recipients_merge_invited_and_participant_contacts(monkeypatch):
    app = _build_app()

    meeting_payload = SimpleNamespace(
        id=5,
        company_id=12,
        title='Reunião Semanal',
        status='completed',
        guests_json=json.dumps({
            'internal': [{'id': 7, 'name': 'Ana'}],
            'external': [{'name': 'Cliente XP', 'email': 'cliente@xp.com', 'whatsapp': '71999990000'}],
        }),
        participants_json=json.dumps({
            'internal': [{'id': 7, 'name': 'Ana'}],
            'external': [{'name': 'Cliente XP'}],
        }),
        agenda_json='[]',
        discussions_json='[]',
        activities_json='[]',
        to_dict=lambda: {
            'id': 5,
            'company_id': 12,
            'title': 'Reunião Semanal',
            'status': 'completed',
            'agenda': [],
            'discussions': [],
            'activities': [],
            'meeting_notes': '',
        },
    )

    monkeypatch.setattr(meeting_resource, 'current_user', SimpleNamespace(is_authenticated=True, id=9, role='admin'))
    monkeypatch.setattr(meeting_resource, 'Meeting', SimpleNamespace(query=_FakeMeetingQuery(meeting_payload)))
    monkeypatch.setattr(meeting_resource, 'Company', SimpleNamespace(query=_FakeCompanyQuery(SimpleNamespace(id=12, is_active=True, name='Empresa Teste'))))
    monkeypatch.setattr(meeting_resource, 'Project', SimpleNamespace(query=_FakeListQuery([])))
    monkeypatch.setattr(
        meeting_resource,
        'Employee',
        SimpleNamespace(
            query=_FakeEmployeeQuery(
                employee=None,
                employees=[SimpleNamespace(id=7, company_id=12, name='Ana', email='ana@empresa.com', whatsapp='71911112222', phone='7133334444')],
            )
        ),
    )

    with app.test_request_context('/meetings/api/meeting/5/summary-recipients?company_id=12'):
        response = meeting_resource.MeetingSummaryRecipientsResource().get.__wrapped__(meeting_resource.MeetingSummaryRecipientsResource(), 5)

    assert response['success'] is True
    recipients = {item['key']: item for item in response['recipients']}

    assert recipients['employee:7']['email'] == 'ana@empresa.com'
    assert recipients['employee:7']['whatsapp'] == '71911112222'
    assert recipients['employee:7']['is_guest'] is True
    assert recipients['employee:7']['is_participant'] is True

    assert recipients['email:cliente@xp.com']['email'] == 'cliente@xp.com'
    assert recipients['email:cliente@xp.com']['whatsapp'] == '71999990000'
    assert recipients['email:cliente@xp.com']['is_guest'] is True
    assert recipients['email:cliente@xp.com']['is_participant'] is True


def test_external_participant_contact_is_directly_eligible_to_receive_minutes(monkeypatch):
    meeting_payload = SimpleNamespace(
        company_id=12,
        guests_json=json.dumps({'internal': [], 'external': []}),
        participants_json=json.dumps({
            'internal': [],
            'external': [{
                'name': 'Consultora Externa',
                'email': 'consultora@example.com',
                'whatsapp': '+5571999990000',
            }],
        }),
    )
    employee_query = _FakeEmployeeQuery(employees=[])
    monkeypatch.setattr(meeting_resource, 'Employee', SimpleNamespace(query=employee_query))

    recipients = meeting_resource._build_meeting_recipients_catalog(meeting_payload)

    assert employee_query.last_filter_kwargs == {'company_id': 12, 'status': 'active'}
    assert recipients == [{
        'key': 'email:consultora@example.com',
        'name': 'Consultora Externa',
        'email': 'consultora@example.com',
        'whatsapp': '5571999990000',
        'employee_id': None,
        'origins': ['participante'],
        'has_email': True,
        'has_whatsapp': True,
        'is_guest': False,
        'is_participant': True,
    }]


def test_meeting_share_summary_sends_selected_channels(monkeypatch):
    app = _build_app()
    sent_emails = []
    sent_whatsapps = []

    meeting_payload = SimpleNamespace(
        id=5,
        company_id=12,
        title='Reunião Estratégica',
        status='completed',
        guests_json=json.dumps({
            'internal': [{'id': 7, 'name': 'Ana'}],
            'external': [],
        }),
        participants_json=json.dumps({
            'internal': [],
            'external': [{'name': 'Cliente XP', 'email': 'cliente@xp.com', 'whatsapp': '71999990000'}],
        }),
        agenda_json=json.dumps([{'title': 'Financeiro'}]),
        discussions_json=json.dumps([{'title': 'Receita', 'discussion': 'Revisar metas do trimestre.'}]),
        activities_json=json.dumps([{'title': 'Atualizar forecast', 'responsible': 'Ana', 'deadline': '2026-03-31'}]),
        to_dict=lambda: {
            'id': 5,
            'company_id': 12,
            'title': 'Reunião Estratégica',
            'status': 'completed',
            'project_id': None,
            'project_title': None,
            'project_code': None,
            'agenda': [{'title': 'Financeiro'}],
            'discussions': [{'title': 'Receita', 'discussion': 'Revisar metas do trimestre.'}],
            'activities': [{'title': 'Atualizar forecast', 'responsible': 'Ana', 'deadline': '2026-03-31'}],
            'meeting_notes': 'Definir próximos passos.',
            'actual_date': '2026-03-27',
            'actual_time': '09:00',
            'scheduled_date': '2026-03-27',
            'scheduled_time': '09:00',
        },
    )

    class _FakeEmailService:
        def build_transactional_email_html(self, subject, body, **kwargs):
            return f'<html><body><h1>{subject}</h1><pre>{body}</pre></body></html>'

        def send_email(self, to_emails, subject, body, html_body=None, attachments=None):
            sent_emails.append({'to_emails': to_emails, 'subject': subject, 'body': body, 'html_body': html_body})
            return True

    class _FakeWhatsAppService:
        def send_message(self, phone_number, message, media_url=None):
            sent_whatsapps.append({'phone_number': phone_number, 'message': message, 'media_url': media_url})
            return True

    monkeypatch.setattr(meeting_resource, 'current_user', SimpleNamespace(is_authenticated=True, id=9, role='admin'))
    monkeypatch.setattr(meeting_resource, 'Meeting', SimpleNamespace(query=_FakeMeetingQuery(meeting_payload)))
    monkeypatch.setattr(meeting_resource, 'Company', SimpleNamespace(query=_FakeCompanyQuery(SimpleNamespace(id=12, is_active=True, name='Empresa Teste'))))
    monkeypatch.setattr(meeting_resource, 'Project', SimpleNamespace(query=_FakeListQuery([])))
    monkeypatch.setattr(
        meeting_resource,
        'Employee',
        SimpleNamespace(
            query=_FakeEmployeeQuery(
                employee=None,
                employees=[SimpleNamespace(id=7, company_id=12, name='Ana', email='ana@empresa.com', whatsapp='71911112222', phone='7133334444')],
            )
        ),
    )
    monkeypatch.setattr(meeting_resource, 'email_service', _FakeEmailService())
    monkeypatch.setattr(meeting_resource, 'whatsapp_service', _FakeWhatsAppService())

    with app.test_request_context(
        '/meetings/api/meeting/5/share-summary?company_id=12',
        method='POST',
        json={
            'channels': ['email', 'whatsapp'],
            'recipient_keys': ['employee:7', 'email:cliente@xp.com'],
        },
    ):
        response = meeting_resource.MeetingShareSummaryResource().post.__wrapped__(meeting_resource.MeetingShareSummaryResource(), 5)

    assert response['success'] is True
    assert response['sent_email'] == 2
    assert response['sent_whatsapp'] == 2
    assert len(sent_emails) == 2
    assert len(sent_whatsapps) == 2
    assert sent_emails[0]['subject'].startswith('Resumo da Reunião:')
    assert 'Ata completa:' in sent_emails[0]['body']
    assert sent_whatsapps[0]['message'].startswith('📋 *RESUMO DA REUNIÃO*')


def test_meeting_sync_activities_respects_activity_project_id(monkeypatch):
    app = _build_app()
    fake_session = _FakeDbSession()

    meeting_payload = SimpleNamespace(
        id=27,
        company_id=8,
        project_id=None,
        meeting_notes='',
        participants_json='[]',
        discussions_json='[]',
        activities_json='[]',
        actual_duration_minutes=None,
        planned_duration_minutes=None,
        status='draft',
        updated_at=None,
    )

    fake_project = SimpleNamespace(id=22, company_id=8, name='Consultoria - Geral', code='C.J.22')

    class _FakeProjectTask:
        query = _FakeFilterAllQuery([])
        project_id = _FakeColumn()

        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

    monkeypatch.setattr(meeting_resource, 'current_user', SimpleNamespace(is_authenticated=True, id=9, role='admin'))
    monkeypatch.setattr(meeting_resource, 'Meeting', SimpleNamespace(query=_FakeMeetingQuery(meeting_payload)))
    monkeypatch.setattr(meeting_resource, 'Company', SimpleNamespace(query=_FakeCompanyQuery(SimpleNamespace(id=8, is_active=True))))
    monkeypatch.setattr(meeting_resource, 'Employee', SimpleNamespace(query=_FakeEmployeeQuery(SimpleNamespace(company_id=8))))
    monkeypatch.setattr(meeting_resource, 'db', SimpleNamespace(session=fake_session))
    monkeypatch.setattr(models, 'ProjectTask', _FakeProjectTask)
    monkeypatch.setattr(meeting_resource, '_load_meeting_target_projects', lambda company_id, project_ids: {22: fake_project})

    with app.test_request_context(
        '/meetings/api/meeting/27/sync-activities?company_id=8',
        method='POST',
        json={
            'activities': [
                {
                    'title': 'Plano de Estruturação da Loja - Adenize',
                    'responsible': 'Adenize',
                    'employee_id': 34,
                    'deadline': '2026-04-20',
                    'budget': 'R$ 12.500',
                    'estimated_hours': 18.5,
                    'priority': 'high',
                    'project_id': 22,
                }
            ]
        },
    ):
        response = meeting_resource.MeetingSyncActivitiesResource().post.__wrapped__(meeting_resource.MeetingSyncActivitiesResource(), 27)

    created_task = fake_session.added[0]
    assert response['success'] is True
    assert response['synced_count'] == 1
    assert created_task.project_id == 22
    assert created_task.what == 'Plano de Estruturação da Loja - Adenize'
    assert created_task.amount == 'R$ 12.500'
    assert created_task.estimated_hours == 18.5
    assert created_task.priority == 'high'
    assert meeting_payload.project_id == 22
    assert fake_session.committed == 1


def test_meeting_sync_rejects_activity_employee_from_other_tenant(monkeypatch):
    app = _build_app()
    fake_session = _FakeDbSession()
    meeting_payload = SimpleNamespace(
        id=27, company_id=8, project_id=22, meeting_notes='', participants_json='[]',
        discussions_json='[]', activities_json='[]', actual_duration_minutes=None,
        planned_duration_minutes=None, status='draft', updated_at=None,
    )
    fake_project = SimpleNamespace(id=22, company_id=8, name='Consultoria', code='C.J.22')

    class _FakeProjectTask:
        query = _FakeFilterAllQuery([])
        project_id = _FakeColumn()

    monkeypatch.setattr(meeting_resource, 'current_user', SimpleNamespace(is_authenticated=True, id=9, role='admin'))
    monkeypatch.setattr(meeting_resource, 'Meeting', SimpleNamespace(query=_FakeMeetingQuery(meeting_payload)))
    monkeypatch.setattr(meeting_resource, 'Company', SimpleNamespace(query=_FakeCompanyQuery(SimpleNamespace(id=8, is_active=True))))
    monkeypatch.setattr(meeting_resource, 'Employee', SimpleNamespace(query=_FakeEmployeeQuery(None)))
    monkeypatch.setattr(meeting_resource, 'db', SimpleNamespace(session=fake_session))
    monkeypatch.setattr(models, 'ProjectTask', _FakeProjectTask)
    monkeypatch.setattr(meeting_resource, '_load_meeting_target_projects', lambda company_id, project_ids: {22: fake_project})

    with app.test_request_context(
        '/meetings/api/meeting/27/sync-activities?company_id=8',
        method='POST',
        json={'activities': [{'title': 'Ação', 'employee_id': 999, 'project_id': 22}]},
    ):
        response, status = meeting_resource.MeetingSyncActivitiesResource().post.__wrapped__(
            meeting_resource.MeetingSyncActivitiesResource(), 27
        )

    assert status == 400
    assert response['success'] is False
    assert 'não pertence à empresa' in response['message']
    assert fake_session.rolled_back is True


def test_meeting_activities_resource_loads_tasks_from_activity_projects(monkeypatch):
    app = _build_app()

    meeting_payload = SimpleNamespace(
        id=27,
        company_id=8,
        project_id=None,
        activities_json=json.dumps([
            {'title': 'Plano de Estruturação da Loja - Adenize', 'project_id': 22, 'responsible': 'Adenize', 'deadline': '2026-04-20'}
        ]),
    )

    fake_project = SimpleNamespace(id=22, company_id=8, name='Consultoria - Geral', code='C.J.22')
    fake_task = SimpleNamespace(
        project_id=22,
        what='Plano de Estruturação da Loja - Adenize',
        who='Adenize',
        employee_name='Adenize',
        due_date=SimpleNamespace(isoformat=lambda: '2026-04-20'),
        to_dict=lambda: {'id': 501, 'project_id': 22},
    )

    class _FakeProjectTaskModel:
        query = _FakeFilterAllQuery([fake_task])
        project_id = _FakeColumn()

    monkeypatch.setattr(meeting_resource, 'current_user', SimpleNamespace(is_authenticated=True, id=9, role='admin'))
    monkeypatch.setattr(meeting_resource, 'Meeting', SimpleNamespace(query=_FakeMeetingQuery(meeting_payload)))
    monkeypatch.setattr(meeting_resource, 'Company', SimpleNamespace(query=_FakeCompanyQuery(SimpleNamespace(id=8, is_active=True))))
    monkeypatch.setattr(meeting_resource, 'Employee', SimpleNamespace(query=_FakeEmployeeQuery(SimpleNamespace(company_id=8))))
    monkeypatch.setattr(models, 'ProjectTask', _FakeProjectTaskModel)
    monkeypatch.setattr(meeting_resource, '_load_meeting_target_projects', lambda company_id, project_ids: {22: fake_project})

    with app.test_request_context('/meetings/api/meeting/27/atividades?company_id=8'):
        response = meeting_resource.MeetingActivitiesResource().get.__wrapped__(meeting_resource.MeetingActivitiesResource(), 27)

    assert response['success'] is True
    assert response['project_id'] == 22
    assert response['project_title'] == 'Consultoria - Geral'
    assert response['project_activities'][0]['project_id'] == 22
    assert response['project_activities'][0]['project_title'] == 'Consultoria - Geral'
    assert response['project_activities'][0]['project_code'] == 'C.J.22'
