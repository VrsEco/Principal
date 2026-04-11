import html as html_module
import os
import sys
from pathlib import Path
from flask import Flask, render_template_string, session
from werkzeug.routing import BuildError

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from api.routes import companies as companies_route


def _build_app():
    app = Flask(__name__, template_folder=os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'templates')))
    app.secret_key = 'test'
    def _safe_url_for(endpoint, **values):
        try:
            from flask import url_for as flask_url_for
            return flask_url_for(endpoint, **values)
        except BuildError:
            return f'/{endpoint.replace(".", "/")}'
    app.jinja_env.globals['url_for'] = _safe_url_for
    app.jinja_env.globals['has_permission'] = lambda *args, **kwargs: True
    app.jinja_env.globals['is_platform_admin'] = lambda *args, **kwargs: True
    app.jinja_env.globals['current_user'] = type('User', (), {'is_authenticated': True, 'name': 'Teste'})()
    return app


def test_sidebar_renders_empresas_group_with_new_structure():
    app = _build_app()
    with app.test_request_context('/companies/new'):
        session['active_company_id'] = 31
        rendered = render_template_string('{% include "partials/sidebar_standard.html" %}')
    html = html_module.unescape(rendered)
    for expected in ['Empresas', 'Lista de empresas', 'Nova empresa / Onboarding', 'Configurações da unidade']:
        assert expected in html
    assert '/companies/31/edit' in html
