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


def test_ai_mcp_console_route_renders_console_with_frontend_state(monkeypatch):
    app = _build_app()
    captured = {}
    active_company = SimpleNamespace(id=31, name="Empresa MCP", client_code="MCP")
    fake_console = {
        "summary": {"profiles": 4, "catalog_tools": 12, "readiness_gates": 5},
        "profiles": [{"profile": "administrador"}],
        "surfaces": [{"surface": "admin"}],
        "domains": [{"domain": "governance"}],
        "permissions": [{"profile": "administrador", "surface": "admin"}],
        "catalog": {"tools": [{"name": "list_app32_capabilities", "domain": "governance", "risk": "low", "scopes": ["mcp_admin"], "permissions": []}]},
        "configuration_links": [{"title": "Console Operacional IA/MCP", "href": "/configs/ai/mcp"}],
        "registration_links": [{"title": "Usuários do sistema", "href": "/auth/users/page"}],
        "operational_links": [{"title": "Sapiens", "href": "/sapiens"}],
        "onboarding": {"steps": []},
        "release": {"checklist": [], "smokes": []},
        "freeze": {"triggers": []},
        "dashboard": {"panels": []},
        "readiness": {"gates": [], "opening_criteria": [], "blocking_conditions": []},
        "readiness_by_phase": [],
    }

    monkeypatch.setattr(configs_route, "_resolve_active_company", lambda: active_company)
    monkeypatch.setattr(configs_route, "_can_access_ai_mcp_console", lambda company_id=None: True)
    monkeypatch.setattr(
        configs_route.AIConfigurationPagesService,
        "build_page",
        lambda page_key, active_company=None: {"title": "MCP", "sections": [], "wizard": {"title": "Assistente", "intro": "", "steps": []}, "hero_metrics": [], "shortcuts": [], "intro": ""},
    )
    monkeypatch.setattr(
        configs_route,
        "render_template",
        lambda template_name, **context: captured.update({"template_name": template_name, "context": context}) or "ok",
    )

    response = app.test_client().get("/configs/ai/mcp")

    assert response.status_code == 200
    assert captured["template_name"] == "modules/operations/ai_config_simple_page.html"
    assert captured["context"]["active_company"].id == 31
    assert captured["context"]["page"]["title"] == "MCP"


def test_ai_tools_route_renders_tools_catalog(monkeypatch):
    app = _build_app()
    captured = {}
    active_company = SimpleNamespace(id=31, name="Empresa MCP", client_code="MCP")
    fake_catalog = {
        "summary": {"domains": 2, "canonical_domains": 1, "wrapper_domains": 1},
        "domains": [{"key": "engineering", "title": "Engenharia"}],
        "discovery": {"rest_endpoint": "/api/configs/ai/mcp/tool-first-catalog"},
    }

    monkeypatch.setattr(configs_route, "_resolve_active_company", lambda: active_company)
    monkeypatch.setattr(configs_route, "_can_access_ai_mcp_console", lambda company_id=None: True)
    monkeypatch.setattr(configs_route.ToolFirstCatalogService, "build_catalog", lambda company=None: fake_catalog)
    monkeypatch.setattr(
        configs_route,
        "render_template",
        lambda template_name, **context: captured.update({"template_name": template_name, "context": context}) or "ok",
    )

    response = app.test_client().get("/configs/ai/tools")

    assert response.status_code == 200
    assert captured["template_name"] == "modules/operations/ai_tools_catalog.html"
    assert captured["context"]["active_company"].id == 31
    assert captured["context"]["tool_catalog"]["summary"]["domains"] == 2


def test_ai_mcp_console_frontend_state_api_returns_payload(monkeypatch):
    app = _build_app()
    active_company = SimpleNamespace(id=9, name="Versus", client_code="VRS")
    fake_console = {"summary": {"catalog_tools": 21}, "profiles": [], "surfaces": [], "domains": [], "permissions": [], "catalog": {"tools": []}, "configuration_links": [], "registration_links": [], "operational_links": [], "onboarding": {"steps": []}, "release": {"checklist": [], "smokes": []}, "freeze": {"triggers": []}, "dashboard": {"panels": []}, "readiness": {"gates": [], "opening_criteria": [], "blocking_conditions": []}, "readiness_by_phase": []}

    monkeypatch.setattr(configs_route, "_resolve_active_company", lambda: active_company)
    monkeypatch.setattr(configs_route, "_can_access_ai_mcp_console", lambda company_id=None: True)
    monkeypatch.setattr(configs_route.AIMCPConsoleService, "build_frontend_state", lambda company=None: fake_console)

    response = app.test_client().get("/api/configs/ai/mcp/frontend-state")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["console"]["summary"]["catalog_tools"] == 21


def test_ai_mcp_tool_first_catalog_api_returns_filtered_payload(monkeypatch):
    app = _build_app()
    active_company = SimpleNamespace(id=31, name="Empresa MCP", client_code="MCP")
    captured = {}
    fake_catalog = {
        "summary": {"domains": 1, "canonical_domains": 1, "wrapper_domains": 0},
        "filters": {"domain": ["engineering"], "status": ["canonical"], "surface": ["engineering"], "include_backlog": False},
        "domains": [{"key": "engineering", "title": "Squad de Engenharia"}],
    }

    def _fake_build(company=None, **kwargs):
        captured["company"] = company
        captured["kwargs"] = kwargs
        return fake_catalog

    monkeypatch.setattr(configs_route, "_resolve_active_company", lambda: active_company)
    monkeypatch.setattr(configs_route, "_can_access_ai_mcp_console", lambda company_id=None: True)
    monkeypatch.setattr(configs_route.ToolFirstCatalogService, "build_catalog", _fake_build)

    response = app.test_client().get(
        "/api/configs/ai/mcp/tool-first-catalog?domain=engineering&status=canonical&surface=engineering&include_backlog=false"
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["catalog"]["summary"]["domains"] == 1
    assert payload["catalog"]["domains"][0]["key"] == "engineering"
    assert captured["company"].id == 31
    assert captured["kwargs"]["domain"] == ["engineering"]
    assert captured["kwargs"]["status"] == ["canonical"]
    assert captured["kwargs"]["surface"] == ["engineering"]
    assert captured["kwargs"]["include_backlog"] is False
