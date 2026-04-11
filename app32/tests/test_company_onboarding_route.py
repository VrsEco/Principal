import html as html_module
import os
import sys
from pathlib import Path

from flask import Flask
from flask_login import LoginManager

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api.routes import companies as companies_route


def _build_app():
    app = Flask(
        __name__,
        template_folder=os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'templates')),
    )
    app.config['TESTING'] = True
    app.config['LOGIN_DISABLED'] = True
    app.secret_key = 'test'
    login_manager = LoginManager(app)

    @login_manager.user_loader
    def _load_user(user_id):
        return None

    app.register_blueprint(companies_route.companies_bp)
    return app


def test_company_new_view_exposes_onboarding_context(monkeypatch):
    app = _build_app()
    captured = {}
    fake_onboarding = {
        'mode': 'create',
        'active_tab': 'dados',
        'header': {'title': 'Crie uma nova empresa', 'subtitle': 'Wizard guiado', 'mode_badge': 'Criação guiada'},
        'steps': [{'id': 'dados', 'number': 1, 'title': 'Quem é a empresa?', 'description': 'Identidade', 'status': 'available'}],
        'domain_tracks': [{'title': 'Rotina'}],
        'context_panel': {'title': 'Quem é a empresa?', 'body': 'Comece pelo básico.', 'items': ['Salvar identidade.']},
        'checklist': ['Salvar identidade.'],
        'quick_links': [{'title': 'Console IA/MCP', 'description': 'Governança', 'href': '/configs/ai/mcp'}],
    }

    monkeypatch.setattr(companies_route.CompanyOnboardingService, 'build_view_model', lambda company_id=None, active_tab='dados': fake_onboarding)
    monkeypatch.setattr(companies_route, 'render_template', lambda template_name, **context: captured.update({'template_name': template_name, 'context': context}) or 'ok')

    with app.test_request_context('/companies/new?tab=dados'):
        response = companies_route.company_new.__wrapped__()

    assert response == 'ok'
    assert captured['template_name'] == 'modules/companies/company_form_v2.html'
    assert captured['context']['active_tab'] == 'dados'
    assert captured['context']['onboarding']['mode'] == 'create'
    assert captured['context']['onboarding']['header']['mode_badge'] == 'Criação guiada'


def test_company_edit_view_exposes_onboarding_context(monkeypatch):
    app = _build_app()
    captured = {}
    fake_onboarding = {
        'mode': 'edit',
        'active_tab': 'config',
        'header': {'title': 'Ajuste a empresa existente', 'subtitle': 'Wizard guiado', 'mode_badge': 'Alteração assistida'},
        'steps': [{'id': 'config', 'number': 7, 'title': 'IA/MCP', 'description': 'Sistema', 'status': 'available'}],
        'domain_tracks': [{'title': 'Sapiens / IA / MCP'}],
        'context_panel': {'title': 'IA/MCP', 'body': 'Finalize o onboarding.', 'items': ['Abrir o console.']},
        'checklist': ['Executar smoke funcional.'],
        'quick_links': [{'title': 'Sapiens', 'description': 'Runtime', 'href': '/sapiens'}],
    }

    monkeypatch.setattr(companies_route.CompanyOnboardingService, 'build_view_model', lambda company_id=None, active_tab='dados': fake_onboarding)
    monkeypatch.setattr(companies_route, 'render_template', lambda template_name, **context: captured.update({'template_name': template_name, 'context': context}) or 'ok')

    with app.test_request_context('/companies/31/edit?tab=config'):
        response = companies_route.company_edit.__wrapped__(31)

    assert response == 'ok'
    assert captured['template_name'] == 'modules/companies/company_form_v2.html'
    assert captured['context']['company_id'] == 31
    assert captured['context']['active_tab'] == 'config'
    assert captured['context']['onboarding']['mode'] == 'edit'
    assert captured['context']['onboarding']['header']['mode_badge'] == 'Alteração assistida'
