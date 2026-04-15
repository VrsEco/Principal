import os
import sys
from types import SimpleNamespace

from flask import Flask
from flask_login import LoginManager

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.routes import configs as configs_route


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

    app.register_blueprint(configs_route.configs_bp)
    return app


def test_factory_context_route_returns_payload(monkeypatch):
    app = _build_app()
    active_company = SimpleNamespace(id=31, name="Versus", client_code="VRS")
    monkeypatch.setattr(configs_route, "_resolve_active_company", lambda: active_company)
    monkeypatch.setattr(configs_route, "_can_access_ai_mcp_console", lambda company_id=None: True)
    monkeypatch.setattr(configs_route, "current_user", SimpleNamespace(id=7, role="admin"))
    monkeypatch.setattr(configs_route, "get_accessible_company_ids", lambda: [31, 32])

    response = app.test_client().get("/api/configs/ai/factory/context")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["actor"]["company_id"] == 31
    assert payload["registry"]["summary"]["capabilities"] >= 1


def test_factory_assess_change_route_validates_and_returns_assessment(monkeypatch):
    app = _build_app()
    active_company = SimpleNamespace(id=31, name="Versus", client_code="VRS")
    monkeypatch.setattr(configs_route, "_resolve_active_company", lambda: active_company)
    monkeypatch.setattr(configs_route, "_can_access_ai_mcp_console", lambda company_id=None: True)
    monkeypatch.setattr(configs_route, "current_user", SimpleNamespace(id=7, role="admin"))
    monkeypatch.setattr(configs_route, "get_accessible_company_ids", lambda: [31])

    response = app.test_client().post(
        "/api/configs/ai/factory/assess-change",
        json={"request_text": "Precisamos evoluir o workflow XYZ pois não está entregando corretamente os resultados."},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["assessment"]["request"]["company_id"] == 31


def test_factory_page_renders(monkeypatch):
    app = _build_app()
    active_company = SimpleNamespace(id=31, name="Versus", client_code="VRS")
    monkeypatch.setattr(configs_route, "_resolve_active_company", lambda: active_company)
    monkeypatch.setattr(configs_route, "_can_access_ai_mcp_console", lambda company_id=None: True)
    monkeypatch.setattr(configs_route, "current_user", SimpleNamespace(id=7, role="admin"))
    monkeypatch.setattr(configs_route, "get_accessible_company_ids", lambda: [31])
    monkeypatch.setattr(configs_route, "render_template", lambda template_name, **kwargs: f"rendered:{template_name}:{kwargs['initial_assessment']['summary']['change_type']}")

    response = app.test_client().get("/ai/factory")

    assert response.status_code == 200
    assert b"rendered:modules/operations/sapiens_factory.html:diagnose" in response.data
