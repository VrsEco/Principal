import os
import sys
from types import SimpleNamespace

from flask import Flask
from flask_login import LoginManager

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.routes import integrations as integrations_route


def _build_app():
    app = Flask(__name__, template_folder=os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "templates")))
    app.config["TESTING"] = True
    app.config["LOGIN_DISABLED"] = True
    app.secret_key = "test"
    login_manager = LoginManager(app)

    @login_manager.user_loader
    def _load_user(user_id):
        return None

    app.register_blueprint(integrations_route.integrations_bp)
    return app


def test_integrations_page_receives_catalog(monkeypatch):
    app = _build_app()
    captured = {}
    monkeypatch.setattr(integrations_route, "_resolve_active_company", lambda: SimpleNamespace(id=31))
    monkeypatch.setattr(
        integrations_route.IntegrationCatalogService,
        "build_api_mcp_catalog",
        lambda: {"summary": {"total": 2}, "integrations": [{"key": "open_finance", "title": "Open Finance"}]},
    )
    monkeypatch.setattr(
        integrations_route,
        "render_template",
        lambda template_name, **context: captured.update({"template": template_name, "context": context}) or "ok",
    )

    response = app.test_client().get("/integrations")

    assert response.status_code == 200
    assert captured["template"] == "integrations.html"
    assert captured["context"]["integration_catalog"]["summary"]["total"] == 2


def test_integrations_requests_page_redirects_to_catalog(monkeypatch):
    app = _build_app()

    response = app.test_client().get("/integrations/requests")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/integrations")


def test_integrations_admin_page_renders(monkeypatch):
    app = _build_app()
    captured = {}
    monkeypatch.setattr(integrations_route, "_resolve_active_company", lambda: SimpleNamespace(id=31))
    monkeypatch.setattr(
        integrations_route.IntegrationCatalogService,
        "build_channel_catalog",
        lambda: {"summary": {"total": 1}, "integrations": [{"key": "service_whatsapp"}]},
    )
    monkeypatch.setattr(
        integrations_route,
        "render_template",
        lambda template_name, **context: captured.update({"template": template_name, "context": context}) or "ok",
    )

    response = app.test_client().get("/integrations/admin")

    assert response.status_code == 200
    assert captured["template"] == "integrations_admin.html"
    assert captured["context"]["integration_catalog"]["summary"]["total"] == 1


def test_integrations_tools_page_renders(monkeypatch):
    app = _build_app()
    captured = {}
    monkeypatch.setattr(integrations_route, "_resolve_active_company", lambda: SimpleNamespace(id=31))
    monkeypatch.setattr(
        integrations_route.ToolFirstCatalogService,
        "build_catalog",
        lambda company=None: {
            "summary": {"domains": 2, "canonical_domains": 1, "wrapper_domains": 1},
            "domains": [{"key": "engineering", "title": "Engenharia"}],
            "discovery": {"rest_endpoint": "/api/configs/ai/mcp/tool-first-catalog"},
        },
    )
    monkeypatch.setattr(
        integrations_route,
        "render_template",
        lambda template_name, **context: captured.update({"template": template_name, "context": context}) or "ok",
    )

    response = app.test_client().get("/integrations/tools")

    assert response.status_code == 200
    assert captured["template"] == "modules/operations/ai_tools_catalog.html"
    assert captured["context"]["tool_catalog"]["summary"]["domains"] == 2


def test_integrations_catalog_api_returns_payload(monkeypatch):
    app = _build_app()
    monkeypatch.setattr(
        integrations_route.IntegrationCatalogService,
        "build_catalog",
        lambda: {"summary": {"total": 4}, "integrations": []},
    )

    response = app.test_client().get("/api/integrations/catalog")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["catalog"]["summary"]["total"] == 4


def test_list_integration_requests_uses_current_user_context(monkeypatch):
    app = _build_app()
    monkeypatch.setattr(integrations_route, "_resolve_active_company", lambda: SimpleNamespace(id=31))
    monkeypatch.setattr(integrations_route, "current_user", SimpleNamespace(id=9, name="Fabiano"))
    captured = {}
    monkeypatch.setattr(
        integrations_route.IntegrationRequestService,
        "list_requests",
        lambda **kwargs: captured.update(kwargs) or [{"id": 1, "title": "Open Finance"}],
    )

    response = app.test_client().get("/api/integrations/requests")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["requests"][0]["title"] == "Open Finance"
    assert captured["company_id"] == 31
    assert captured["requester_user_id"] == 9
    assert captured["requester_name"] == "Fabiano"


def test_create_integration_request_uses_active_company_and_current_user(monkeypatch):
    app = _build_app()
    monkeypatch.setattr(integrations_route, "_resolve_active_company", lambda: SimpleNamespace(id=31))
    monkeypatch.setattr(integrations_route, "current_user", SimpleNamespace(id=9, name="Fabiano"))
    monkeypatch.setattr(
        integrations_route.IntegrationRequestService,
        "create_request",
        lambda payload, **kwargs: SimpleNamespace(to_dict=lambda: {"id": 7, "backlog_task_id": 456, **payload}),
    )

    response = app.test_client().post(
        "/api/integrations/requests",
        json={
            "title": "Open Finance",
            "business_domain": "Financeiro",
            "integration_mode": "consume",
            "technical_channel": "api_mcp",
            "external_system": "Banco X",
            "objective": "Consumir extratos bancários para conciliação operacional.",
            "data_summary": "Extratos e saldos.",
            "source_channel": "ui_integrations_catalog",
        },
    )
    payload = response.get_json()

    assert response.status_code == 201
    assert payload["success"] is True
    assert payload["request"]["backlog_task_id"] == 456
