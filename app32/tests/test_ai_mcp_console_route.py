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


def test_ai_mcp_legacy_route_redirects_to_api_mcp(monkeypatch):
    app = _build_app()

    response = app.test_client().get("/configs/ai/mcp")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/api-mcp")


def test_ai_tools_route_redirects_to_integrations_tools(monkeypatch):
    app = _build_app()

    response = app.test_client().get("/configs/ai/tools")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/tools")


def test_ai_mcp_console_frontend_state_api_returns_payload(monkeypatch):
    app = _build_app()
    active_company = SimpleNamespace(id=9, name="Versus", client_code="VRS")
    fake_console = {"summary": {"catalog_tools": 21}, "profiles": [], "surfaces": [], "domains": [], "permissions": [], "catalog": {"tools": [], "context_requirements": {"company_only": 2}}, "configuration_links": [], "registration_links": [], "operational_links": [], "onboarding": {"steps": []}, "release": {"checklist": [], "smokes": []}, "freeze": {"triggers": []}, "dashboard": {"panels": []}, "readiness": {"gates": [], "opening_criteria": [], "blocking_conditions": []}, "readiness_by_phase": [], "connection_generator": {"defaults": {}, "modes": []}, "documentation_bootstrap": {"endpoint": "/api/configs/ai/mcp/bootstrap-session", "default_surface": "user", "auto_load": True, "summary": {"catalog_version": "2026-05-08.1", "features_total": 2, "domains": ["routine"], "context_summary": {"company_only": 2}, "current_context": {"required": ["company"]}}}, "runtime_context": {"resolved": {"company_id": 9}, "resolution": {"company": "active_company"}}}

    monkeypatch.setattr(configs_route, "_resolve_active_company", lambda: active_company)
    monkeypatch.setattr(configs_route, "_can_access_ai_mcp_console", lambda company_id=None: True)
    monkeypatch.setattr(configs_route.AIMCPConsoleService, "build_frontend_state", lambda company=None: fake_console)

    response = app.test_client().get("/api/configs/ai/mcp/frontend-state")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["console"]["summary"]["catalog_tools"] == 21
    assert payload["console"]["catalog"]["context_requirements"]["company_only"] == 2
    assert payload["console"]["runtime_context"]["resolved"]["company_id"] == 9


def test_ai_mcp_console_template_includes_instruction_registry_panel():
    template_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "templates",
            "modules",
            "operations",
            "ai_mcp_console.html",
        )
    )

    with open(template_path, "r", encoding="utf-8") as handle:
        body = handle.read()

    assert "Instruction Registry" in body
    assert "Sapiens On + bootstrap instrucional" in body
    assert "Filtro runtime" in body
    assert "Modo de edição" in body
    assert "Mudanças recentes" in body


def test_ai_mcp_bootstrap_session_api_returns_payload(monkeypatch):
    app = _build_app()
    active_company = SimpleNamespace(id=31, name="Empresa MCP", client_code="MCP")

    monkeypatch.setattr(configs_route, "_resolve_active_company", lambda: active_company)
    monkeypatch.setattr(configs_route, "_can_access_ai_mcp_console", lambda company_id=None: True)

    class _FakeUser:
        id = 7

    monkeypatch.setattr(configs_route, "current_user", _FakeUser())

    class _FakeService:
        def bootstrap_context(self, context, domain=None, search=None):
            return {
                "company_id": context.company_id,
                "user_id": context.user_id,
                "surface": context.surface,
                "catalog_version": "2026-05-08.1",
                "domains": ["routine"],
                "features": [{"id": "rotina_tarefas", "nome": "Tarefas da Rotina", "required_context": ["company"]}],
                "current_context": {"required": ["company"], "resolved": {"company_id": context.company_id}},
                "context_summary": {"company_only": 1},
            }

    monkeypatch.setattr(configs_route, "MCPFeatureCatalogService", _FakeService, raising=False)

    response = app.test_client().get("/api/configs/ai/mcp/bootstrap-session?surface=user")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["bootstrap"]["company_id"] == 31
    assert payload["bootstrap"]["surface"] == "user"
    assert payload["bootstrap"]["features"][0]["id"] == "rotina_tarefas"
    assert payload["bootstrap"]["current_context"]["resolved"]["company_id"] == 31
    assert payload["bootstrap"]["context_summary"]["company_only"] == 1


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


def test_ai_mcp_connection_snippet_api_returns_prompt(monkeypatch):
    app = _build_app()
    active_company = SimpleNamespace(id=31, name="Empresa MCP", client_code="MCP")

    monkeypatch.setattr(configs_route, "_resolve_active_company", lambda: active_company)
    monkeypatch.setattr(configs_route, "_can_access_ai_mcp_console", lambda company_id=None: True)

    response = app.test_client().post(
        "/api/configs/ai/mcp/connection-snippet",
        json={
            "mode": "ai_prompt",
            "name": "Sapiens User",
            "default_company": "Sem empresa padrão",
            "url": "https://app.gestaoversus.com.br/mcp/user",
            "auth_type": "bearer",
            "token": "token-123",
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["mode"] == "ai_prompt"
    assert "◆ SAPIENS · Gestão Versus ● ativo" in payload["content"]
    assert "Este cliente não suporta ativação automática do Sapiens." in payload["content"]
    assert '"auth_type": "bearer"' in payload["source_json"]


def test_ai_mcp_connection_snippet_api_validates_missing_token(monkeypatch):
    app = _build_app()
    active_company = SimpleNamespace(id=31, name="Empresa MCP", client_code="MCP")

    monkeypatch.setattr(configs_route, "_resolve_active_company", lambda: active_company)
    monkeypatch.setattr(configs_route, "_can_access_ai_mcp_console", lambda company_id=None: True)

    response = app.test_client().post(
        "/api/configs/ai/mcp/connection-snippet",
        json={
            "mode": "raw_config",
            "name": "Sapiens User",
            "default_company": "Sem empresa padrão",
            "url": "https://app.gestaoversus.com.br/mcp/user",
            "auth_type": "bearer",
            "token": "",
        },
    )

    assert response.status_code == 400
    payload = response.get_json()
    assert payload["success"] is False
    assert "Token Bearer" in payload["error"]


def test_ai_mcp_console_service_exposes_context_requirements_and_runtime_context():
    from services.ai_mcp_console_service import AIMCPConsoleService

    active_company = SimpleNamespace(id=9, name="Versus", client_code="VRS")
    payload = AIMCPConsoleService.build_frontend_state(active_company)

    assert "context_requirements" in payload["catalog"]
    assert payload["runtime_context"]["resolved"]["company_id"] == 9
    assert payload["runtime_context"]["resolution"]["company"] == "active_company"
    assert "instruction_registry" in payload
    assert payload["instruction_registry"]["endpoints"]["frontend_state"] == "/api/configs/ai/mcp/instruction-registry/frontend-state"
    assert payload["instruction_registry"]["endpoints"]["promote"] == "/api/configs/ai/mcp/instruction-registry/promote"
    assert "squad_cliente" in payload["instruction_registry"]["supported_runtimes"]
    assert "status_distribution" in payload["instruction_registry"]["summary"]
    assert "production" in payload["instruction_registry"]["supported_environments"]


def test_ai_mcp_console_service_exposes_squad_versus_runtime_profile():
    from services.ai_mcp_console_service import AIMCPConsoleService

    active_company = SimpleNamespace(id=9, name="Versus", client_code="VRS")
    payload = AIMCPConsoleService.build_frontend_state(active_company)

    runtime_profiles = {item["key"]: item for item in payload["external_runtime_profiles"]}
    squad_versus = runtime_profiles["squad_versus"]

    assert squad_versus["surface"] == "admin"
    assert "profiles" in squad_versus["required_contracts"]
    assert "list_admin_app32_capabilities" in squad_versus["startup_tools"]
    assert payload["connection_generator"]["defaults"]["profile"] == "sapiens_default"


def test_ai_mcp_console_service_exposes_squad_cliente_runtime_profile():
    from services.ai_mcp_console_service import AIMCPConsoleService

    active_company = SimpleNamespace(id=9, name="Versus", client_code="VRS")
    payload = AIMCPConsoleService.build_frontend_state(active_company)

    runtime_profiles = {item["key"]: item for item in payload["external_runtime_profiles"]}
    squad_cliente = runtime_profiles["squad_cliente"]

    assert squad_cliente["surface"] == "user"
    assert "surface_playbooks" in squad_cliente["required_contracts"]
    assert "list_user_app32_capabilities" in squad_cliente["startup_tools"]
    assert "describe_app32_profile_contracts_tool" in squad_cliente["startup_tools"]
    assert squad_cliente["default_harness_key"] == "harness_coordenador_cliente_v1"
    assert squad_cliente["official_phase_label"] == "Fase 1 oficial"
    assert [item["key"] for item in squad_cliente["official_agents"]] == [
        "SC-COORD",
        "SC-COM",
        "SC-OPS",
        "SC-ADM",
    ]
    assert [item["key"] for item in squad_cliente["harnesses"]] == [
        "harness_coordenador_cliente_v1",
        "harness_comercial_cliente_v1",
        "harness_operacional_cliente_v1",
        "harness_admfin_cliente_v1",
    ]
    assert "resolve_app32_instruction_bundle_tool" in squad_cliente["startup_tools"]


def test_ai_mcp_console_service_exposes_assisted_usage_and_maturity_model():
    from services.ai_mcp_console_service import AIMCPConsoleService

    active_company = SimpleNamespace(id=9, name="Versus", client_code="VRS")
    payload = AIMCPConsoleService.build_frontend_state(active_company)

    assert payload["assisted_usage"]["phases"][0]["key"] == "conducao_forte"
    assert "consultor_versus" in payload["maturity_model"]["signals"]
    assert "usuario_cliente" in payload["maturity_model"]["signals"]


def test_ai_mcp_console_service_exposes_governance_telemetry(monkeypatch):
    from services.ai_mcp_console_service import AIMCPConsoleService

    monkeypatch.setattr(
        "services.operational_audit_service.OperationalAuditService.build_panel",
        lambda **kwargs: (
            {
                "summary": {"total": 3, "by_source": {"ai_mcp_runtime": 3}, "by_status": {"success": 2, "blocked": 1}},
                "analytics": {
                    "by_runtime": {"mcp": 3},
                    "by_actor_role": {"administrador": 2},
                    "by_surface": {"admin": 3},
                    "by_runtime_profile": {"squad_versus": 2},
                    "top_tools": [{"name": "list_app32_capabilities", "count": 2}],
                },
            },
            None,
        ),
    )

    active_company = SimpleNamespace(id=9, name="Versus", client_code="VRS")
    payload = AIMCPConsoleService.build_frontend_state(active_company)

    assert payload["governance_telemetry"]["enabled"] is True
    assert payload["governance_telemetry"]["summary"]["total"] == 3
    assert payload["governance_telemetry"]["analytics"]["by_runtime_profile"]["squad_versus"] == 2


def test_ai_mcp_console_service_exposes_versus_and_engineering_harness_families():
    from services.ai_mcp_console_service import AIMCPConsoleService

    active_company = SimpleNamespace(id=9, name="Versus", client_code="VRS")
    payload = AIMCPConsoleService.build_frontend_state(active_company)

    runtime_profiles = {item["key"]: item for item in payload["external_runtime_profiles"]}
    squad_versus = runtime_profiles["squad_versus"]
    engineering = runtime_profiles["engineering"]

    assert squad_versus["default_harness_key"] == "harness_coordenador_versus_v1"
    assert any(item["key"] == "harness_finance_versus_v1" for item in squad_versus["harnesses"])
    assert engineering["surface"] == "ops"
    assert engineering["default_harness_key"] == "harness_coordenador_engenharia_v1"
    assert any(item["key"] == "harness_backend_api_engenharia_v1" for item in engineering["harnesses"])

    connection_profiles = {item["key"]: item for item in payload["connection_generator"]["profiles"]}
    assert connection_profiles["squad_versus"]["default_harness_key"] == "harness_coordenador_versus_v1"
    assert connection_profiles["engineering"]["surface"] == "ops"
    assert connection_profiles["squad_cliente"]["official_phase_label"] == "Fase 1 oficial"
