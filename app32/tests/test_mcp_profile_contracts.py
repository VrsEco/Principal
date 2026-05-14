import pytest

from src.core.mcp_profile_contract_tools import register_profile_contract_tools
from src.intelligence.mcp_contracts import APP32_PROFILE_CONTRACTS_MANIFEST
from src.intelligence.security.tool_policy import ToolPolicyRequest, evaluate_tool_policy


class _FakeMCP:
    def __init__(self):
        self.registered = {}

    def tool(self, *args, **kwargs):
        def decorator(func):
            self.registered[kwargs.get("name") or func.__name__] = func
            return func

        if args and callable(args[0]):
            return decorator(args[0])
        return decorator


def test_profile_contracts_cover_all_supported_profiles():
    profiles = {profile.profile for profile in APP32_PROFILE_CONTRACTS_MANIFEST.profiles}
    assert profiles == {"colaborador", "cliente", "administrador", "admin_tecnico"}
    overlays = {overlay.overlay for overlay in APP32_PROFILE_CONTRACTS_MANIFEST.role_overlays}
    assert {
        "coordenador_cliente",
        "comercial_cliente",
        "operacional_cliente",
        "admfin_cliente",
        "estrategico_cliente",
        "pessoas_capacidade_cliente",
        "coordenador_versus",
        "strategist_versus",
        "pmo_controller_versus",
        "business_architect_versus",
        "operations_versus",
        "followup_collector_versus",
        "performance_analyst_versus",
        "finance_versus",
        "auditor_versus",
        "coordenador_engenharia",
        "arquiteto_engenharia",
        "frontend_engenharia",
        "backend_api_engenharia",
        "backend_service_engenharia",
        "ai_engineer_engenharia",
        "dba_engenharia",
        "qa_automation_engenharia",
    } == overlays


def test_cliente_is_restricted_to_user_read_or_limited_actions():
    cliente = APP32_PROFILE_CONTRACTS_MANIFEST.get_profile("cliente")

    assert cliente is not None
    assert cliente.allowed_surfaces == ["user"]
    assert cliente.can_execute_financial_mutations is False
    assert "finance" in cliente.forbidden_domains
    assert "workload" in cliente.forbidden_domains
    assert "identity_self_service" in cliente.allowed_domains
    assert "processes" in cliente.allowed_domains
    assert "identity_admin" in cliente.forbidden_domains


def test_administrador_and_admin_tecnico_surface_matrix():
    administrador = APP32_PROFILE_CONTRACTS_MANIFEST.get_profile("administrador")
    admin_tecnico = APP32_PROFILE_CONTRACTS_MANIFEST.get_profile("admin_tecnico")

    assert administrador is not None
    assert admin_tecnico is not None

    assert set(administrador.allowed_surfaces) == {"user", "admin", "analytics"}
    assert "ops" not in administrador.allowed_surfaces
    assert set(admin_tecnico.allowed_surfaces) == {"admin", "analytics", "ops"}
    assert "identity_admin" in administrador.allowed_domains
    assert "processes" in administrador.allowed_domains
    assert "identity_self_service" in administrador.allowed_domains
    assert "workload" in administrador.allowed_domains
    assert "identity_admin" in admin_tecnico.allowed_domains
    assert "processes" in admin_tecnico.allowed_domains
    assert "workload" in admin_tecnico.allowed_domains


def test_profile_contract_tool_returns_manifest_and_profile():
    mcp = _FakeMCP()
    register_profile_contract_tools(mcp)
    tool = mcp.registered["describe_app32_profile_contracts_tool"]

    manifest = tool()
    profile = tool("administrador_tecnico")
    overlay = tool(overlay_role="operacional_cliente")
    runtime_family = tool(runtime_profile="squad_cliente")
    invalid = tool("foo")

    assert manifest["success"] is True
    assert len(manifest["data"]["profiles"]) == 4
    assert len(manifest["data"]["role_overlays"]) == 23
    assert profile["success"] is True
    assert profile["data"]["profile"] == "admin_tecnico"
    assert overlay["success"] is True
    assert overlay["data"]["overlay"] == "operacional_cliente"
    assert runtime_family["success"] is True
    assert runtime_family["data"]["runtime_profile"] == "squad_cliente"
    assert runtime_family["data"]["official_phase_label"] == "Fase 1 oficial"
    assert [item["overlay"] for item in runtime_family["data"]["official_overlays"]] == [
        "coordenador_cliente",
        "comercial_cliente",
        "operacional_cliente",
        "admfin_cliente",
    ]
    assert invalid["success"] is False
    assert invalid["error"]["code"] == "profile_contract_not_found"


def test_tool_policy_enforces_surface_by_profile_contract():
    blocked = evaluate_tool_policy(
        {"user_id": 10, "company_id": 7, "role": "colaborador"},
        ToolPolicyRequest(
            tool_name="query_database",
            surface="analytics",
            domain="analytics",
            action="read",
            requested_company_id=7,
        ),
    )
    allowed = evaluate_tool_policy(
        {"user_id": 1, "company_id": 7, "role": "administrador_tecnico"},
        ToolPolicyRequest(
            tool_name="inspect_runtime",
            surface="ops",
            domain="diagnostics",
            action="read",
            requested_company_id=7,
        ),
    )

    assert blocked.allowed is False
    assert "surface analytics não permitida" in blocked.reason
    assert "surface_not_allowed_for_profile" in blocked.checks
    assert allowed.allowed is True


def test_cliente_overlay_contracts_keep_finance_blocked_and_user_surface_only():
    overlay = APP32_PROFILE_CONTRACTS_MANIFEST.get_overlay("admfin_cliente")

    assert overlay is not None
    assert overlay.runtime_profile == "squad_cliente"
    assert overlay.surface == "user"
    assert "finance" in overlay.blocked_domains
    assert "finance" not in overlay.allowed_domains


def test_versus_and_engineering_overlay_contracts_reflect_family_and_surface():
    versus = APP32_PROFILE_CONTRACTS_MANIFEST.get_overlay("finance_versus")
    engineering = APP32_PROFILE_CONTRACTS_MANIFEST.get_overlay("backend_service_engenharia")

    assert versus is not None
    assert versus.runtime_profile == "squad_versus"
    assert versus.surface == "admin"
    assert "finance" in versus.allowed_domains
    assert "update" in versus.allowed_actions

    assert engineering is not None
    assert engineering.runtime_profile == "engineering"
    assert engineering.surface == "ops"
    assert "processes" in engineering.allowed_domains
    assert "update" in engineering.allowed_actions
