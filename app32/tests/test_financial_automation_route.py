import os
import sys
from types import SimpleNamespace

from flask import Flask
from flask_login import LoginManager

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.routes import financial_automation as automation_route
from utils import permissions as permission_utils


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

    app.register_blueprint(automation_route.financial_automation_bp)
    return app


def test_financial_automation_page_renders_central(monkeypatch):
    app = _build_app()
    monkeypatch.setattr(permission_utils, "has_permission", lambda company_id, resource, action: True)
    monkeypatch.setattr(
        automation_route,
        "get_active_company",
        lambda: SimpleNamespace(id=9, to_dict=lambda: {"id": 9, "name": "Empresa Teste"}),
    )
    monkeypatch.setattr(
        automation_route,
        "render_template",
        lambda template_name, **context: f"{template_name}|{context.get('company_id')}",
    )

    client = app.test_client()
    response = client.get("/financial/automation", follow_redirects=False)

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "modules/financial/automation_center.html" in html
    assert html.endswith("|9")


def test_app_registers_financial_automation_blueprint_and_resources():
    app_source = open(
        r"C:\GestaoVersus\app32\app32\app.py",
        "r",
        encoding="utf-8",
    ).read()

    assert "from api.routes.financial_automation import financial_automation_bp" in app_source
    assert "app.register_blueprint(financial_automation_bp)" in app_source
    assert "FinancialAutomationOptionsResource" in app_source
    assert "/api/financial/automation/options" in app_source
    assert "/api/financial/automation/records" in app_source
