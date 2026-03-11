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
