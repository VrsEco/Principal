import os
import sys
from types import SimpleNamespace

from flask import Flask
from flask_login import LoginManager
from werkzeug.exceptions import Forbidden

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


def test_api_mcp_page_receives_catalog(monkeypatch):
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

    response = app.test_client().get("/api-mcp")

    assert response.status_code == 200
    assert captured["template"] == "integrations.html"
    assert captured["context"]["integration_catalog"]["summary"]["total"] == 2


def test_integrations_legacy_route_redirects_to_api_mcp(monkeypatch):
    app = _build_app()

    response = app.test_client().get("/integrations")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/api-mcp")


def test_integrations_requests_page_redirects_to_catalog(monkeypatch):
    app = _build_app()

    response = app.test_client().get("/integrations/requests")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/api-mcp")


def test_channels_page_renders(monkeypatch):
    app = _build_app()
    captured = {}
    monkeypatch.setattr(integrations_route, "_resolve_active_company", lambda: SimpleNamespace(id=31))
    monkeypatch.setattr(integrations_route, "_require_integration_admin", lambda company_id=None: None)
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

    response = app.test_client().get("/channels")

    assert response.status_code == 200
    assert captured["template"] == "integrations_admin.html"
    assert captured["context"]["integration_catalog"]["summary"]["total"] == 1


def test_tools_page_renders(monkeypatch):
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

    response = app.test_client().get("/tools")

    assert response.status_code == 200
    assert captured["template"] == "modules/operations/ai_tools_catalog.html"
    assert captured["context"]["tool_catalog"]["summary"]["domains"] == 2


def test_workflow_page_renders(monkeypatch):
    app = _build_app()
    captured = {}
    monkeypatch.setattr(integrations_route, "_resolve_active_company", lambda: SimpleNamespace(id=31))
    monkeypatch.setattr(
        integrations_route.WorkflowWorkspaceService,
        "build_catalog",
        lambda company=None: {
            "summary": {"workflow_count": 2, "active_workflow_count": 2},
            "workflows": [{"code": "1.4", "title": "Cadastrar Atividade", "is_active": True}],
        },
    )
    monkeypatch.setattr(
        integrations_route,
        "render_template",
        lambda template_name, **context: captured.update({"template": template_name, "context": context}) or "ok",
    )

    response = app.test_client().get("/workflow")

    assert response.status_code == 200
    assert captured["template"] == "workflows.html"
    assert captured["context"]["workflow_catalog"]["summary"]["workflow_count"] == 2


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


def test_channels_page_requires_integration_admin(monkeypatch):
    app = _build_app()
    monkeypatch.setattr(integrations_route, "_resolve_active_company", lambda: SimpleNamespace(id=31))
    monkeypatch.setattr(integrations_route, "_require_integration_admin", lambda company_id=None: (_ for _ in ()).throw(Forbidden()))

    response = app.test_client().get("/channels")

    assert response.status_code == 403


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


def test_list_tool_requests_uses_current_user_context(monkeypatch):
    app = _build_app()
    monkeypatch.setattr(integrations_route, "_resolve_active_company", lambda: SimpleNamespace(id=31))
    monkeypatch.setattr(integrations_route, "current_user", SimpleNamespace(id=9, name="Fabiano"))
    captured = {}
    monkeypatch.setattr(
        integrations_route.ToolBacklogService,
        "list_requests",
        lambda **kwargs: captured.update(kwargs) or [{"id": "tool:engineering:publish_tool_contract", "title": "publish_tool_contract"}],
    )

    response = app.test_client().get("/api/integrations/tools/requests")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["requests"][0]["title"] == "publish_tool_contract"
    assert captured["active_company"].id == 31
    assert captured["requester_user_id"] == 9
    assert captured["requester_name"] == "Fabiano"


def test_create_tool_request_uses_current_user_context(monkeypatch):
    app = _build_app()
    monkeypatch.setattr(integrations_route, "_resolve_active_company", lambda: SimpleNamespace(id=31))
    monkeypatch.setattr(integrations_route, "current_user", SimpleNamespace(id=9, name="Fabiano"))
    captured = {}
    monkeypatch.setattr(
        integrations_route.ToolBacklogService,
        "create_request",
        lambda payload, **kwargs: captured.update({"payload": payload, **kwargs}) or {"id": "manual:999", "backlog_task_code": "AA.J.31.999"},
    )

    response = app.test_client().post(
        "/api/integrations/tools/requests",
        json={
            "title": "calculate_budget_variance",
            "business_domain": "Financeiro",
            "objective": "Comparar orçamento e realizado por centro de resultado.",
            "data_summary": "budget_id, period, cost_center_id",
            "source_channel": "ui_tools_catalog",
        },
    )
    payload = response.get_json()

    assert response.status_code == 201
    assert payload["success"] is True
    assert payload["request"]["backlog_task_code"] == "AA.J.31.999"
    assert captured["company_id"] == 31
    assert captured["requester_user_id"] == 9
    assert captured["requester_name"] == "Fabiano"


def test_list_workflow_requests_uses_current_user_context(monkeypatch):
    app = _build_app()
    monkeypatch.setattr(integrations_route, "_resolve_active_company", lambda: SimpleNamespace(id=31))
    monkeypatch.setattr(integrations_route, "current_user", SimpleNamespace(id=9, name="Fabiano"))
    captured = {}
    monkeypatch.setattr(
        integrations_route.WorkflowBacklogService,
        "list_requests",
        lambda **kwargs: captured.update(kwargs) or [{"id": "manual:999", "title": "followup_operacional"}],
    )

    response = app.test_client().get("/api/integrations/workflows/requests")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["requests"][0]["title"] == "followup_operacional"
    assert captured["active_company"].id == 31
    assert captured["requester_user_id"] == 9


def test_create_workflow_request_uses_current_user_context(monkeypatch):
    app = _build_app()
    monkeypatch.setattr(integrations_route, "_resolve_active_company", lambda: SimpleNamespace(id=31))
    monkeypatch.setattr(integrations_route, "current_user", SimpleNamespace(id=9, name="Fabiano"))
    captured = {}
    monkeypatch.setattr(
        integrations_route.WorkflowBacklogService,
        "create_request",
        lambda payload, **kwargs: captured.update({"payload": payload, **kwargs}) or {"id": "manual:1001", "backlog_task_code": "AA.J.31.1001"},
    )

    response = app.test_client().post(
        "/api/integrations/workflows/requests",
        json={
            "title": "fechamento_financeiro_guiado",
            "business_domain": "Financeiro",
            "objective": "Conduzir fechamento com coleta, validação e confirmação.",
            "data_summary": "empresa, período, checkpoints, aprovações",
            "source_channel": "ui_workflows_catalog",
        },
    )
    payload = response.get_json()

    assert response.status_code == 201
    assert payload["success"] is True
    assert payload["request"]["backlog_task_code"] == "AA.J.31.1001"
    assert captured["company_id"] == 31
    assert captured["requester_user_id"] == 9


def test_build_workflow_spec_draft_route(monkeypatch):
    app = _build_app()
    monkeypatch.setattr(integrations_route, "current_user", SimpleNamespace(id=9, name="Fabiano"))
    monkeypatch.setattr(
        integrations_route.WorkflowSpecDraftService,
        "build_draft",
        lambda payload: {"suggested_action_key": "financeiro.execute_fechamento", "channels": ["web"]},
    )

    response = app.test_client().post(
        "/api/integrations/workflows/spec-draft",
        json={
            "title": "Fechamento Financeiro Guiado",
            "business_domain": "Financeiro",
            "objective": "Conduzir fechamento com segurança.",
            "problem_statement": "Hoje há retrabalho e risco operacional.",
            "target_users": "Financeiro",
            "desired_channels": "web",
            "expected_result": "Fechamento concluído com checklist.",
            "user_examples": "Quero fechar o financeiro da empresa X.",
        },
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["spec_draft"]["suggested_action_key"] == "financeiro.execute_fechamento"


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


def test_create_or_update_integration_requires_admin(monkeypatch):
    app = _build_app()
    monkeypatch.setattr(integrations_route, "_resolve_active_company", lambda: SimpleNamespace(id=31))
    monkeypatch.setattr(integrations_route, "_require_integration_admin", lambda company_id=None: (_ for _ in ()).throw(Forbidden()))

    response = app.test_client().post(
        "/api/integrations",
        json={
            "name": "Integração WhatsApp",
            "provider": "z-api",
            "type": "whatsapp",
            "auth_type": "z-api",
            "config": {"api_key": "abc", "instance_id": "inst"},
        },
    )

    assert response.status_code == 403


def test_create_or_update_integration_rejects_unknown_fields(monkeypatch):
    app = _build_app()
    monkeypatch.setattr(integrations_route, "_resolve_active_company", lambda: SimpleNamespace(id=31))
    monkeypatch.setattr(integrations_route, "_require_integration_admin", lambda company_id=None: None)

    response = app.test_client().post(
        "/api/integrations",
        json={
            "name": "Integração WhatsApp",
            "provider": "z-api",
            "type": "whatsapp",
            "auth_type": "z-api",
            "config": {"api_key": "abc", "instance_id": "inst"},
            "unexpected_field": "boom",
        },
    )
    payload = response.get_json()

    assert response.status_code == 400
    assert payload["success"] is False
    assert "Payload inválido" in payload["error"]


def test_create_or_update_integration_scopes_payload_to_active_company(monkeypatch):
    app = _build_app()
    monkeypatch.setattr(integrations_route, "_resolve_active_company", lambda: SimpleNamespace(id=31))
    monkeypatch.setattr(integrations_route, "_require_integration_admin", lambda company_id=None: None)
    captured = {}
    monkeypatch.setattr(
        integrations_route,
        "create_integration",
        lambda payload, company_id=None: captured.update({"payload": payload, "company_id": company_id}) or True,
    )
    monkeypatch.setattr(
        integrations_route,
        "get_integration",
        lambda integration_id, company_id=None, **kwargs: {"id": integration_id, "company_id": company_id, "type": "whatsapp", "provider": "z-api", "config": {"provider": "z-api"}},
    )

    response = app.test_client().post(
        "/api/integrations",
        json={
            "name": "Integração WhatsApp",
            "provider": "z-api",
            "type": "whatsapp",
            "auth_type": "z-api",
            "config": {"api_key": "abc", "instance_id": "inst"},
        },
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    assert captured["company_id"] == 31
    assert captured["payload"]["company_id"] == 31
    assert captured["payload"]["id"] == "company_31_whatsapp_integration"


def test_get_integrations_lists_only_active_company_scope(monkeypatch):
    app = _build_app()
    monkeypatch.setattr(integrations_route, "_resolve_active_company", lambda: SimpleNamespace(id=31))
    monkeypatch.setattr(integrations_route, "_require_integration_admin", lambda company_id=None: None)
    captured = {}
    monkeypatch.setattr(
        integrations_route,
        "list_integrations",
        lambda company_id=None, **kwargs: captured.update({"company_id": company_id, **kwargs}) or [
            {"id": "company_31_email_integration", "company_id": 31, "type": "email", "provider": "smtp", "config": {"provider": "smtp"}},
        ],
    )

    response = app.test_client().get("/api/integrations")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    assert captured["company_id"] == 31
    assert payload["integrations"][0]["id"] == "company_31_email_integration"
