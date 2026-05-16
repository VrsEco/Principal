import pytest
from pydantic import ValidationError

from src.core.mcp_domain_playbook_tools import register_domain_playbook_tools
from src.intelligence.mcp_contracts import (
    APP32_ALLOWED_ANALYSIS_CATALOG,
    APP32_CRUD_CONTRACTS_MANIFEST,
    APP32_DOMAIN_PLAYBOOKS_MANIFEST,
    DomainPlaybook,
    DomainPromptPolicy,
)


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


def test_domain_playbooks_cover_core_domains_and_aliases():
    domains = {playbook.domain for playbook in APP32_DOMAIN_PLAYBOOKS_MANIFEST.playbooks}

    assert {
        "routine",
        "processes",
        "projects",
        "meetings",
        "strategy",
        "finance",
        "analytics",
        "workload",
        "identity_self_service",
        "identity_admin",
        "operations",
        "governance",
    } <= domains
    assert APP32_DOMAIN_PLAYBOOKS_MANIFEST.get_domain("tasks").domain == "routine"
    assert APP32_DOMAIN_PLAYBOOKS_MANIFEST.get_domain("team_capacity").domain == "workload"
    assert APP32_DOMAIN_PLAYBOOKS_MANIFEST.get_domain("identity").domain == "identity_self_service"


def test_domain_playbooks_align_with_crud_and_analysis_catalogs():
    manifest_domains = {playbook.domain for playbook in APP32_DOMAIN_PLAYBOOKS_MANIFEST.playbooks}
    crud_domains = {contract.domain for contract in APP32_CRUD_CONTRACTS_MANIFEST.domains}
    analysis_domains = {analysis.domain for analysis in APP32_ALLOWED_ANALYSIS_CATALOG.analyses}

    assert crud_domains <= manifest_domains
    assert analysis_domains <= manifest_domains
    assert all(playbook.tenant_scope_required for playbook in APP32_DOMAIN_PLAYBOOKS_MANIFEST.playbooks)
    assert all(not playbook.sql_freeform_allowed for playbook in APP32_DOMAIN_PLAYBOOKS_MANIFEST.playbooks)


def test_domain_playbook_security_boundaries():
    finance = APP32_DOMAIN_PLAYBOOKS_MANIFEST.get_domain("finance")
    analytics = APP32_DOMAIN_PLAYBOOKS_MANIFEST.get_domain("analytics")
    operations = APP32_DOMAIN_PLAYBOOKS_MANIFEST.get_domain("operations")
    identity_self_service = APP32_DOMAIN_PLAYBOOKS_MANIFEST.get_domain("identity_self_service")
    identity_admin = APP32_DOMAIN_PLAYBOOKS_MANIFEST.get_domain("identity_admin")

    assert finance is not None
    assert {"colaborador", "administrador", "admin_tecnico"} <= set(finance.allowed_profiles)
    assert "user" in finance.allowed_surfaces
    assert "admfin_cliente" in finance.allowed_role_overlays
    assert "finance_versus" in finance.allowed_role_overlays
    assert analytics is not None
    assert "analytics" in analytics.allowed_surfaces
    assert any("não gerar sql livre" in shortcut.lower() for shortcut in analytics.forbidden_shortcuts)
    assert operations is not None
    assert operations.allowed_profiles == ["admin_tecnico"]
    assert "coordenador_engenharia" in operations.allowed_role_overlays
    assert identity_self_service is not None
    assert "user" in identity_self_service.allowed_surfaces
    assert "cliente" in identity_self_service.allowed_profiles
    assert "coordenador_cliente" in identity_self_service.allowed_role_overlays
    assert identity_admin is not None
    assert "user" not in identity_admin.allowed_surfaces
    assert set(identity_admin.allowed_profiles) == {"administrador", "admin_tecnico"}


def test_describe_domain_playbooks_tool_returns_manifest_and_domain_payloads():
    mcp = _FakeMCP()
    register_domain_playbook_tools(mcp)
    tool = mcp.registered["describe_app32_domain_playbooks_tool"]

    manifest_payload = tool()
    assert manifest_payload["success"] is True
    assert manifest_payload["meta"]["operation"] == "domain_playbooks.describe"
    assert manifest_payload["data"]["version"] == "app32.mcp.domain-playbooks.v1"

    project_payload = tool("projects")
    assert project_payload["success"] is True
    assert project_payload["data"]["domain"] == "projects"

    alias_payload = tool("worklog")
    assert alias_payload["success"] is True
    assert alias_payload["data"]["domain"] == "routine"


def test_describe_domain_playbooks_tool_rejects_unknown_domain():
    mcp = _FakeMCP()
    register_domain_playbook_tools(mcp)
    tool = mcp.registered["describe_app32_domain_playbooks_tool"]

    payload = tool("unknown")

    assert payload["success"] is False
    assert payload["error"]["code"] == "domain_playbook_not_found"


def test_domain_playbook_forbids_extra_fields_and_sql_freeform():
    prompt_policy = DomainPromptPolicy(
        system_preamble="Você opera o domínio com company_id obrigatório e sem atalhos inseguros.",
        required_context=["company_id", "user_id"],
        planning_rules=["Descobrir capabilities.", "Validar contrato."],
        refusal_rules=["Recusar SQL livre."],
        output_contract="Responder com filtros, contrato e resultado permitido.",
    )

    with pytest.raises(ValidationError):
        DomainPlaybook(
            domain="analytics",
            title="Analytics",
            objective="Playbook analítico seguro.",
            allowed_surfaces=["analytics"],
            allowed_profiles=["administrador"],
            canonical_tools=["describe_app32_allowed_analyses_tool"],
            canonical_artifacts=["src.intelligence.mcp_contracts.analysis_catalog"],
            discovery_sequence=["descobrir", "executar"],
            prompt_policy=prompt_policy,
            analysis_rules=["Sem SQL livre."],
            forbidden_shortcuts=["Não gerar SQL livre."],
            escalation_rules=["Escalar ausência de read model."],
            sql_freeform_allowed=True,
            unexpected="blocked",  # type: ignore[arg-type]
        )


def test_domain_playbooks_expose_versus_and_engineering_overlays_by_domain():
    strategy = APP32_DOMAIN_PLAYBOOKS_MANIFEST.get_domain("strategy")
    analytics = APP32_DOMAIN_PLAYBOOKS_MANIFEST.get_domain("analytics")

    assert strategy is not None
    assert "strategist_versus" in strategy.allowed_role_overlays
    assert "backend_api_engenharia" in strategy.allowed_role_overlays

    assert analytics is not None
    assert "auditor_versus" in analytics.allowed_role_overlays
    assert "dba_engenharia" in analytics.allowed_role_overlays
