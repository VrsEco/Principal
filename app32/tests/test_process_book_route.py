import os
import sys
from types import SimpleNamespace

from flask import Flask, session

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api.routes import processes as process_routes
from services import process_book_service


class _FakeProcessQuery:
    def __init__(self, process_obj):
        self.process_obj = process_obj

    def get_or_404(self, process_id):
        return self.process_obj


def _build_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'test'
    app.config['TESTING'] = True
    app.config['LOGIN_DISABLED'] = True
    return app


def test_process_book_route_uses_process_company_scope(monkeypatch):
    app = _build_app()
    fake_process = SimpleNamespace(id=112, company_id=9, name='Processo Book')

    monkeypatch.setattr(process_routes, 'current_user', SimpleNamespace(is_authenticated=True))
    monkeypatch.setattr(process_routes, 'has_permission', lambda company_id, resource, action: company_id == 9)
    monkeypatch.setattr(process_routes, 'Process', SimpleNamespace(query=_FakeProcessQuery(fake_process)))
    monkeypatch.setattr(process_routes, 'is_collaborator_in_company', lambda company_id: False)
    monkeypatch.setattr(
        process_book_service,
        'build_process_book_context',
        lambda process_id, company_id, request_root=None: {
            'process': fake_process,
            'company': SimpleNamespace(id=9, name='Empresa 9'),
            'generated_at': '11/03/2026 12:00',
            'first_page': {'title': 'BOOK', 'stats': []},
            'pop_activities': [],
            'routines': [],
            'indicators': [],
        },
    )
    monkeypatch.setattr(process_routes, 'render_template', lambda template, **ctx: {'template': template, 'context': ctx})

    with app.test_request_context('/processes/112/book'):
        response = process_routes.process_book.__wrapped__(112)
        active_company_id = session['active_company_id']

    assert active_company_id == 9
    assert response['template'] == 'reports/process_book_v2.html'
    assert response['context']['process'].company_id == 9
    assert response['context']['company'].id == 9


def test_process_details_template_contains_book_action():
    template_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            '..',
            'templates',
            'modules',
            'processes',
            'process_details_v2.html',
        )
    )
    with open(template_path, 'r', encoding='utf-8') as handle:
        content = handle.read()

    assert "url_for('processes.process_book', process_id=process_id)" in content
    assert 'Versão de Impressão' in content
    assert 'Abrir Book' not in content


def test_process_book_template_keeps_published_snapshot_without_runtime_bpmn_mutation():
    template_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            '..',
            'templates',
            'reports',
            'process_book_v2.html',
        )
    )
    with open(template_path, 'r', encoding='utf-8') as handle:
        content = handle.read()

    assert '@page process-flow-landscape' in content
    assert 'margin: 8mm' in content
    assert '{{ first_page.bpmn_svg|safe }}' in content
    assert 'function prepareBpmnBookFlow()' not in content
    assert 'const BOOK_BPMN_TASK_FONT_SCALE = 1.5;' not in content
    assert '.pop-section {' not in content
    assert '.section-flow .page-inner {' in content
    assert 'break-after: auto !important;' in content
    assert 'page-break-after: auto !important;' in content
    assert 'height: calc(210mm - 16mm);' in content
    assert 'display: block;' in content
    assert 'max-height: 100%;' in content
    assert '.section-flow + .section-page {' in content
    assert '<h2>Fluxo do processo</h2>' not in content
    assert 'Fluxo em página exclusiva, em paisagem, para melhor leitura e impressão.' not in content


def test_process_book_places_operational_artifacts_between_pop_and_routines():
    template_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            '..',
            'templates',
            'reports',
            'process_book_v2.html',
        )
    )
    with open(template_path, 'r', encoding='utf-8') as handle:
        content = handle.read()

    pop_idx = content.index('<h2>POP - Procedimento Operacional Padrão</h2>')
    artifacts_idx = content.index('<h2>Formulários e checklists operacionais</h2>')
    routines_idx = content.index('<h2>Rotinas</h2>')

    assert pop_idx < artifacts_idx < routines_idx
