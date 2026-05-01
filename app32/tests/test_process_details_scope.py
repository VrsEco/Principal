import os
import sys
from types import SimpleNamespace

from flask import Flask, session

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api.routes import processes as process_routes
from api.resources import process as process_resource


class _FakeProcessQuery:
    def __init__(self, process_obj):
        self.process_obj = process_obj
        self.requested_id = None

    def get_or_404(self, process_id):
        self.requested_id = process_id
        return self.process_obj


class _FakeCompanyQuery:
    def __init__(self, company_obj):
        self.company_obj = company_obj
        self.requested_id = None

    def get_or_404(self, company_id):
        self.requested_id = company_id
        return self.company_obj


def _build_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'test'
    app.config['TESTING'] = True
    app.config['LOGIN_DISABLED'] = True
    return app


def test_process_details_route_syncs_active_company_from_process(monkeypatch):
    app = _build_app()
    fake_process = SimpleNamespace(id=287, company_id=22, name='Processo X')
    fake_company = SimpleNamespace(id=22, name='Empresa X')

    monkeypatch.setattr(process_routes, 'current_user', SimpleNamespace(is_authenticated=True, role='collaborator'))
    monkeypatch.setattr(process_routes, 'has_permission', lambda company_id, resource, action: company_id == 22)
    monkeypatch.setattr(process_routes, 'Process', SimpleNamespace(query=_FakeProcessQuery(fake_process)))
    monkeypatch.setattr(process_routes, 'Company', SimpleNamespace(query=_FakeCompanyQuery(fake_company)))
    monkeypatch.setattr(process_routes, 'is_collaborator_in_company', lambda company_id: False)
    monkeypatch.setattr(process_routes, '_build_process_details_payload', lambda process: {'company_id': process.company_id, 'name': process.name})
    monkeypatch.setattr(process_routes, 'render_template', lambda template, **ctx: {'template': template, 'context': ctx})

    with app.test_request_context('/processes/287'):
        response = process_routes.process_details.__wrapped__(287)
        active_company_id = session['active_company_id']

    assert active_company_id == 22
    assert response['template'] == 'modules/processes/process_details_v2.html'
    assert response['context']['process'].company_id == 22
    assert response['context']['company'].id == 22
    assert response['context']['company_id'] == 22
    assert response['context']['process_payload']['company_id'] == 22
    assert response['context']['process_payload']['name'] == 'Processo X'


def test_process_bpmn_modeler_route_exposes_asset_version(monkeypatch):
    app = _build_app()
    fake_process = SimpleNamespace(id=287, company_id=22, name='Processo X')
    fake_company = SimpleNamespace(id=22, name='Empresa X')

    monkeypatch.setattr(process_routes, 'current_user', SimpleNamespace(is_authenticated=True, role='collaborator'))
    monkeypatch.setattr(process_routes, 'has_permission', lambda company_id, resource, action: company_id == 22)
    monkeypatch.setattr(process_routes, 'Process', SimpleNamespace(query=_FakeProcessQuery(fake_process)))
    monkeypatch.setattr(process_routes, 'Company', SimpleNamespace(query=_FakeCompanyQuery(fake_company)))
    monkeypatch.setattr(process_routes, 'is_collaborator_in_company', lambda company_id: False)
    monkeypatch.setattr(process_routes, '_process_bpmn_modeler_asset_version', lambda: '123456')
    monkeypatch.setattr(process_routes, 'render_template', lambda template, **ctx: {'template': template, 'context': ctx})

    with app.test_request_context('/processes/287/bpmn-modeler'):
        response = process_routes.process_bpmn_modeler.__wrapped__(287)

    assert response['template'] == 'modules/processes/bpmn_modeler.html'
    assert response['context']['company_id'] == 22
    assert response['context']['asset_version'] == '123456'


def test_process_resource_checks_permission_against_process_company(monkeypatch):
    app = _build_app()
    fake_process = SimpleNamespace(id=287, company_id=44)
    checked = {}

    monkeypatch.setattr(process_resource, 'current_user', SimpleNamespace(is_authenticated=True, role='collaborator'))
    monkeypatch.setattr(process_resource, 'Process', SimpleNamespace(query=_FakeProcessQuery(fake_process)))

    def fake_has_permission(company_id, resource, action):
        checked['company_id'] = company_id
        checked['resource'] = resource
        checked['action'] = action
        return False

    monkeypatch.setattr(process_resource, 'has_permission', fake_has_permission)

    with app.test_request_context('/api/processes/287'):
        response, status = process_resource.ProcessResource().get.__wrapped__(process_resource.ProcessResource(), 287)

    assert status == 403
    assert response['error'] == 'Permission denied: view on processes'
    assert checked == {'company_id': 44, 'resource': 'processes', 'action': 'view'}


def test_process_details_template_uses_resilient_loading():
    template_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'templates', 'modules', 'processes', 'process_details_v2.html'))
    with open(template_path, 'r', encoding='utf-8') as handle:
        content = handle.read()

    assert 'Promise.allSettled' in content
    assert 'Falha parcial ao carregar' in content


def test_bpmn_modeler_template_cache_busts_served_assets():
    template_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'templates', 'modules', 'processes', 'bpmn_modeler.html'))
    with open(template_path, 'r', encoding='utf-8') as handle:
        content = handle.read()

    assert "filename='css/process_bpmn_modeler.css', v=asset_version" in content
    assert "filename='js/process_bpmn_modeler.js', v=asset_version" in content


def test_occurrences_loader_sends_company_scope_and_falls_back_gracefully():
    js_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'static', 'js', 'process_details_occurrences.js'))
    with open(js_path, 'r', encoding='utf-8') as handle:
        content = handle.read()

    assert "query.set('company_id', companyId)" in content
    assert 'state.occurrences = []' in content



def test_process_details_template_removes_occurrences_module():
    template_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'templates', 'modules', 'processes', 'process_details_v2.html'))
    with open(template_path, 'r', encoding='utf-8') as handle:
        content = handle.read()

    assert 'tab-occurrences' not in content
    assert 'occurrenceModal' not in content
    assert 'process_details_occurrences.js' not in content
    assert 'fetchOccurrences()' not in content


def test_process_details_template_bootstraps_initial_payload_and_fallback():
    template_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'templates', 'modules', 'processes', 'process_details_v2.html'))
    with open(template_path, 'r', encoding='utf-8') as handle:
        content = handle.read()

    assert 'const initialProcess = {{ process_payload|tojson }};' in content
    assert 'state.process: initialProcess' not in content
    assert 'process: initialProcess || null' in content
    assert 'mantendo payload inicial da rota SSR' in content
    assert 'function setElementText(id, value)' in content
    assert "Elemento ausente no DOM" in content


def test_process_details_template_uses_app32_visual_pattern():
    template_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'templates', 'modules', 'processes', 'process_details_v2.html'))
    with open(template_path, 'r', encoding='utf-8') as handle:
        content = handle.read()

    assert 'process-hero' in content
    assert 'process-kpi-card' in content
    assert 'process-tabs-nav' in content
    assert 'process-section__eyebrow' in content
    assert 'process-indicators-list' in content
    assert 'instance-card--highlight' in content
    assert 'btn-instance-action' in content
    assert 'compact-meta' in content
    assert 'indicator-process-card' not in content


def test_process_details_template_exposes_back_to_kanban_action():
    template_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'templates', 'modules', 'processes', 'process_details_v2.html'))
    with open(template_path, 'r', encoding='utf-8') as handle:
        content = handle.read()

    assert "url_for('processes.processes_list', company_id=company.id)" in content
    assert 'Voltar ao Kanban' in content
