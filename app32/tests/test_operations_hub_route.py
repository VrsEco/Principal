import os
from pathlib import Path
from types import SimpleNamespace

from flask import Flask, render_template_string
from flask_login import LoginManager


BASE_DIR = Path(__file__).resolve().parents[1]


def _build_app():
    app = Flask(
        __name__,
        template_folder=os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "templates")),
    )
    app.config["TESTING"] = True
    app.config["LOGIN_DISABLED"] = True
    app.secret_key = "test"
    login_manager = LoginManager(app)

    @login_manager.user_loader
    def _load_user(user_id):
        return None

    return app


def test_operations_hub_template_promotes_automation_center():
    template = (BASE_DIR / "templates" / "modules" / "operations" / "hub.html").read_text(encoding="utf-8")

    assert "Abrir central financeira" in template
    assert "Abrir piloto financeiro" not in template
    assert "Central de Automação" in template
    assert "Importação, validação e geração financeira assistida" in template
    assert "/financial/automation" in template
    assert "/api-mcp" in template
    assert "/sapiens" in template



def test_operations_hub_template_renders_real_jinja():
    app = _build_app()
    modules = [
        {
            "key": "technical",
            "label": "Plataforma IA",
            "description": "Governança de IA",
            "groups": [
                {
                    "label": "Backoffice técnico",
                    "items": [
                        {
                            "title": "Parâmetros gerais de IA",
                            "description": "Configurar agentes.",
                            "href": "/ai",
                            "mode": "Configuração IA",
                        }
                    ],
                }
            ],
        }
    ]

    with app.test_request_context("/operations"):
        html = render_template_string(
            '{% extends "modules/operations/hub.html" %}{% block sidebar_left %}{% endblock %}',
            active_company=SimpleNamespace(id=9, name="GanduInvest", client_code="GND"),
            modules=modules,
        )

    assert "Parâmetros gerais de IA" in html
    assert "/api-mcp" in html
    assert "/ai" in html
