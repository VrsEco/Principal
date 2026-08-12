import os
import sys
from types import SimpleNamespace

from flask import Flask, session

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api.routes import processes as process_routes
from services.process_portal_service import _attach_artifacts_to_pop_activities


class _FakeCompanyQuery:
    def __init__(self, company_obj):
        self.company_obj = company_obj

    def get(self, company_id):
        return self.company_obj

    def get_or_404(self, company_id):
        return self.company_obj


def _build_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'test'
    app.config['TESTING'] = True
    app.config['LOGIN_DISABLED'] = True
    return app


def test_process_portal_page_syncs_active_company(monkeypatch):
    app = _build_app()
    fake_company = SimpleNamespace(id=22, name='Empresa X')

    monkeypatch.setattr(process_routes, 'Company', SimpleNamespace(query=_FakeCompanyQuery(fake_company)))
    monkeypatch.setattr(process_routes, '_get_current_company_employee', lambda company_id: SimpleNamespace(id=91))
    monkeypatch.setattr(process_routes, 'is_collaborator_in_company', lambda company_id: False)
    monkeypatch.setattr(
        process_routes,
        '_build_process_map_compact_context',
        lambda company_id: {'company': fake_company, 'company_id': company_id},
    )
    monkeypatch.setattr(process_routes, 'render_template', lambda template, **ctx: {'template': template, 'context': ctx})

    with app.test_request_context('/companies/22/process-portal'):
        response = process_routes.process_portal_page.__wrapped__(22)
        active_company_id = session['active_company_id']

    assert active_company_id == 22
    assert response['template'] == 'modules/processes/process_portal_compact.html'
    assert response['context']['company'].id == 22


def test_process_portal_summary_route_uses_company_scope(monkeypatch):
    app = _build_app()
    captured = {}

    monkeypatch.setattr(process_routes, '_get_current_company_employee', lambda company_id: SimpleNamespace(id=31))
    monkeypatch.setattr(process_routes, 'has_company_full_access', lambda company_id: company_id == 9)
    monkeypatch.setattr(
        process_routes,
        'build_process_portal_summary',
        lambda company_id, current_employee_id=None, can_manage_all=False: captured.update({
            'company_id': company_id,
            'current_employee_id': current_employee_id,
            'can_manage_all': can_manage_all,
        }) or {'company': {'id': company_id}, 'summary': {}, 'areas': []},
    )

    with app.test_request_context('/api/companies/9/process-portal'):
        response = process_routes.api_process_portal_summary.__wrapped__(9)
        payload = response.get_json()

    assert payload['ok'] is True
    assert captured == {'company_id': 9, 'current_employee_id': 31, 'can_manage_all': True}


def test_process_portal_detail_route_translates_access_error(monkeypatch):
    app = _build_app()

    monkeypatch.setattr(process_routes, '_get_current_company_employee', lambda company_id: SimpleNamespace(id=18))
    monkeypatch.setattr(process_routes, 'has_company_full_access', lambda company_id: False)

    def _raise_access(*args, **kwargs):
        raise process_routes.ProcessPortalAccessError('Sem vínculo')

    monkeypatch.setattr(process_routes, 'build_process_portal_process_detail', _raise_access)

    with app.test_request_context('/api/companies/9/process-portal/processes/44'):
        response, status = process_routes.api_process_portal_process_detail.__wrapped__(9, 44)
        payload = response.get_json()

    assert status == 403
    assert payload['ok'] is False
    assert payload['error'] == 'Sem vínculo'


def test_process_portal_detail_route_translates_unexpected_error(monkeypatch):
    app = _build_app()

    monkeypatch.setattr(process_routes, '_get_current_company_employee', lambda company_id: SimpleNamespace(id=18))
    monkeypatch.setattr(process_routes, 'has_company_full_access', lambda company_id: False)

    def _raise_unexpected(*args, **kwargs):
        raise NameError('and_ is not defined')

    monkeypatch.setattr(process_routes, 'build_process_portal_process_detail', _raise_unexpected)

    with app.test_request_context('/api/companies/9/process-portal/processes/22'):
        response, status = process_routes.api_process_portal_process_detail.__wrapped__(9, 22)
        payload = response.get_json()

    assert status == 500
    assert payload['ok'] is False
    assert payload['error'] == process_routes.PUBLIC_ERROR_MESSAGE


def test_process_portal_template_contains_visual_portal_sections():
    template_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            '..',
            'templates',
            'modules',
            'processes',
            'process_portal.html',
        )
    )
    with open(template_path, 'r', encoding='utf-8') as handle:
        content = handle.read()

    assert 'Portal de Processos' in content
    assert 'Biblioteca do Processo' in content
    assert 'processPortalModal' in content
    assert 'data-summary-url' in content


def test_portal_attaches_only_artifacts_linked_to_same_bpmn_activity():
    pop_activities = [
        {'id': 1, 'bpmn_element_id': 'Task_A'},
        {'id': 2, 'bpmn_element_id': 'Task_B'},
    ]
    artifacts = [
        {
            'id': 10,
            'artifact_type': 'form',
            'name': 'Formulário A',
            'activity_links': [
                {
                    'id': 100,
                    'bpmn_element_id': 'Task_A',
                    'is_required': True,
                    'completion_policy_json': {'allow_skip': False},
                }
            ],
        },
        {
            'id': 11,
            'artifact_type': 'check',
            'name': 'Checklist B',
            'activity_links': [
                {'id': 101, 'bpmn_element_id': 'Task_B', 'is_required': False}
            ],
        },
    ]

    _attach_artifacts_to_pop_activities(pop_activities, artifacts)

    assert [item['id'] for item in pop_activities[0]['artifacts']] == [10]
    assert pop_activities[0]['artifacts'][0]['is_required'] is True
    assert pop_activities[0]['artifacts'][0]['activity_link']['id'] == 100
    assert [item['id'] for item in pop_activities[1]['artifacts']] == [11]


def test_process_portal_detail_exposes_forms_checks_and_pop_integration():
    template_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            '..',
            'templates',
            'modules',
            'processes',
            'process_portal_process_detail.html',
        )
    )
    with open(template_path, 'r', encoding='utf-8') as handle:
        content = handle.read()

    assert 'data-action="forms"' in content
    assert 'data-action="checks"' in content
    assert 'renderOperationalArtifacts' in content
    assert 'renderPopArtifacts(activity.artifacts || [])' in content
