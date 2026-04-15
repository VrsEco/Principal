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
    monkeypatch.setattr(configs_route.AICapabilityInventoryService, "build_inventory", lambda active_company=None: {"summary": {"capabilities": 1}})
    monkeypatch.setattr(configs_route.AIAutomationRegistryService, "build_registry", lambda active_company=None: {"summary": {"automations": 1}})

    response = app.test_client().get("/api/configs/ai/factory/context")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["actor"]["company_id"] == 31
    assert payload["registry"]["summary"]["capabilities"] >= 1
    assert payload["inventory"]["summary"]["capabilities"] == 1


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


def test_factory_blueprint_route_returns_payload(monkeypatch):
    app = _build_app()
    active_company = SimpleNamespace(id=31, name="Versus", client_code="VRS")
    monkeypatch.setattr(configs_route, "_resolve_active_company", lambda: active_company)
    monkeypatch.setattr(configs_route, "_can_access_ai_mcp_console", lambda company_id=None: True)

    response = app.test_client().get("/api/configs/ai/capability-blueprint?title=Teste&domain=engineering")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["blueprint"]["domain"] == "engineering"


def test_inventory_and_automation_pages_render(monkeypatch):
    app = _build_app()
    active_company = SimpleNamespace(id=31, name="Versus", client_code="VRS")
    monkeypatch.setattr(configs_route, "_resolve_active_company", lambda: active_company)
    monkeypatch.setattr(configs_route, "_require_ai_admin_access", lambda company_id=None: None)
    monkeypatch.setattr(configs_route, "_render_ai_config_page", lambda page_key, active_company=None: f"page:{page_key}:{getattr(active_company, 'id', None)}")

    inventory_response = app.test_client().get("/ai-capability-inventory")
    automation_response = app.test_client().get("/ai-automation-mesh")

    assert inventory_response.status_code == 200
    assert automation_response.status_code == 200
    assert b"page:inventory:31" in inventory_response.data
    assert b"page:automation_mesh:31" in automation_response.data


def test_factory_create_backlog_card_returns_task(monkeypatch):
    app = _build_app()
    active_company = SimpleNamespace(id=31, name="Versus", client_code="VRS")
    monkeypatch.setattr(configs_route, "_resolve_active_company", lambda: active_company)
    monkeypatch.setattr(configs_route, "_can_access_ai_mcp_console", lambda company_id=None: True)
    monkeypatch.setattr(configs_route, "current_user", SimpleNamespace(id=7, role="admin"))
    monkeypatch.setattr(configs_route, "get_accessible_company_ids", lambda: [31])
    monkeypatch.setattr(
        configs_route,
        "create_backlog_task",
        lambda **kwargs: (
            SimpleNamespace(id=1418, code="AA.J.31.1418", what=kwargs["title"]),
            None,
        ),
    )

    response = app.test_client().post(
        "/api/configs/ai/factory/create-backlog-card",
        json={"request_text": "Precisamos evoluir o workflow XYZ pois não está entregando corretamente os resultados."},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["backlog_task"]["code"] == "AA.J.31.1418"


def test_factory_actor_context_handles_admin_unrestricted_access(monkeypatch):
    active_company = SimpleNamespace(id=31, name="Versus", client_code="VRS")
    monkeypatch.setattr(configs_route, "current_user", SimpleNamespace(id=7, role="admin"))
    monkeypatch.setattr(configs_route, "get_accessible_company_ids", lambda: None)

    actor = configs_route._build_factory_actor_context(active_company)

    assert actor.company_id == 31
    assert actor.accessible_company_ids == [31]
