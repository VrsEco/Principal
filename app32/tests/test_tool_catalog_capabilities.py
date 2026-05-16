from dataclasses import dataclass

from src.intelligence.tool_catalog import catalog
from src.intelligence.tooling.capabilities import ToolRiskLevel, ToolScope
from src.intelligence.tooling.registry import ToolCapabilityRegistry


@dataclass
class DummyTool:
    name: str
    description: str = ""


def test_catalog_exposes_known_capability_metadata():
    capability = catalog.get_tool_capability("query_database")
    self_service_capability = catalog.get_tool_capability("list_my_companies")
    company_profile_capability = catalog.get_tool_capability("get_company_profile")
    company_update_capability = catalog.get_tool_capability("update_company_profile")
    admin_identity_capability = catalog.get_tool_capability("list_system_users")
    engineering_suggestion_capability = catalog.get_tool_capability("request_engineering_suggestion")
    update_macro_capability = catalog.get_tool_capability("update_macro_process")
    financial_entry_capability = catalog.get_tool_capability("create_financial_entry")

    assert capability is not None
    assert capability.domain == "analytics"
    assert capability.risk == ToolRiskLevel.HIGH
    assert ToolScope.MCP_ANALYTICS.value in capability.scopes
    assert ToolScope.MCP_ADMIN.value not in capability.scopes
    assert capability.human_gate is True
    assert self_service_capability is not None
    assert self_service_capability.domain == "identity_self_service"
    assert company_profile_capability is not None
    assert company_profile_capability.domain == "identity_self_service"
    assert company_update_capability is not None
    assert company_update_capability.domain == "identity_self_service"
    assert company_update_capability.risk == ToolRiskLevel.MEDIUM
    assert admin_identity_capability is not None
    assert admin_identity_capability.domain == "identity_admin"
    assert engineering_suggestion_capability is not None
    assert engineering_suggestion_capability.domain == "operations"
    assert ToolScope.MCP_USER.value in engineering_suggestion_capability.scopes
    assert update_macro_capability is not None
    assert update_macro_capability.domain == "processes"
    assert financial_entry_capability is not None
    assert financial_entry_capability.domain == "finance"
    assert ToolScope.MCP_USER.value in financial_entry_capability.scopes
    assert "financial.create" in financial_entry_capability.permissions


def test_catalog_manifest_filters_by_scope():
    admin_manifest = catalog.get_capability_manifest(scope=ToolScope.MCP_ADMIN, include_tools=True)
    analytics_manifest = catalog.get_capability_manifest(scope=ToolScope.MCP_ANALYTICS, include_tools=True)
    user_manifest = catalog.get_capability_manifest(scope=ToolScope.MCP_USER, include_tools=True)

    admin_tool_names = {tool["name"] for tool in admin_manifest["tools"]}
    analytics_tool_names = {tool["name"] for tool in analytics_manifest["tools"]}
    user_tool_names = {tool["name"] for tool in user_manifest["tools"]}

    assert "query_database" not in admin_tool_names
    assert "query_database" in analytics_tool_names
    assert "query_database" not in user_tool_names
    assert "get_plan_diagnostics_read_model" in analytics_tool_names
    assert "get_team_workload_read_model" in analytics_tool_names
    assert "get_projects_execution_risk_read_model" in analytics_tool_names
    assert "list_my_companies" in admin_tool_names
    assert "list_my_companies" in user_tool_names
    assert "get_company_profile" in admin_tool_names
    assert "get_company_profile" in user_tool_names
    assert "update_company_profile" in admin_tool_names
    assert "update_company_profile" in user_tool_names
    assert "request_engineering_suggestion" in admin_tool_names
    assert "request_engineering_suggestion" in user_tool_names
    assert "list_my_engineering_suggestions" in user_tool_names
    assert "update_macro_process" in user_tool_names


def test_catalog_manifest_supports_legacy_identity_domain_alias():
    identity_manifest = catalog.get_capability_manifest(domain="identity", include_tools=True)
    identity_tool_names = {tool["name"] for tool in identity_manifest["tools"]}

    assert "list_my_companies" in identity_tool_names
    assert "get_company_profile" in identity_tool_names
    assert "update_company_profile" in identity_tool_names
    assert "update_user_contacts" in identity_tool_names
    assert "list_system_users" in identity_tool_names
    assert "register_system_user" in identity_tool_names


def test_registry_infers_capabilities_for_unknown_tools():
    registry = ToolCapabilityRegistry.from_tools(
        [
            DummyTool(name="create_budget_entry", description="Cria lançamento de orçamento"),
            DummyTool(name="get_finance_dashboard", description="Consulta dashboard financeiro"),
        ]
    )

    create_capability = registry.get("create_budget_entry")
    read_capability = registry.get("get_finance_dashboard")

    assert create_capability is not None
    assert create_capability.risk in {ToolRiskLevel.MEDIUM, ToolRiskLevel.HIGH}
    assert ToolScope.SAPIENS.value in create_capability.scopes

    assert read_capability is not None
    assert read_capability.domain == "finance"
    assert read_capability.risk == ToolRiskLevel.LOW
