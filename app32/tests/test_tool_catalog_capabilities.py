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
    list_meetings_capability = catalog.get_tool_capability("list_meetings")
    delete_meeting_capability = catalog.get_tool_capability("delete_meeting_secure")
    pop_media_capability = catalog.get_tool_capability("get_process_pop_step_media_context_tool")
    pop_draft_capability = catalog.get_tool_capability("draft_process_pop_step_description_tool")
    strategy_update_capability = catalog.get_tool_capability("update_plan_section")
    strategy_diag_capability = catalog.get_tool_capability("get_plan_diagnostics")
    strategy_global_okr_capability = catalog.get_tool_capability("create_global_okr")
    strategy_area_okr_capability = catalog.get_tool_capability("create_area_okr")
    strategy_global_kr_capability = catalog.get_tool_capability("create_global_key_result")
    strategy_area_kr_capability = catalog.get_tool_capability("create_area_key_result")

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
    assert list_meetings_capability is not None
    assert list_meetings_capability.domain == "meetings"
    assert "meeting.read" in list_meetings_capability.permissions
    assert delete_meeting_capability is not None
    assert delete_meeting_capability.domain == "meetings"
    assert ToolScope.MCP_ADMIN.value in delete_meeting_capability.scopes
    assert ToolScope.MCP_USER.value not in delete_meeting_capability.scopes
    assert delete_meeting_capability.human_gate is True
    assert pop_media_capability is not None
    assert pop_media_capability.domain == "processes"
    assert ToolScope.MCP_USER.value in pop_media_capability.scopes
    assert pop_draft_capability is not None
    assert pop_draft_capability.domain == "processes"
    assert pop_draft_capability.risk == ToolRiskLevel.MEDIUM
    assert strategy_update_capability is not None
    assert strategy_update_capability.domain == "strategy"
    assert strategy_update_capability.human_gate is True
    assert ToolScope.MCP_ADMIN.value in strategy_update_capability.scopes
    assert strategy_diag_capability is not None
    assert strategy_diag_capability.domain == "strategy"
    assert ToolScope.MCP_USER.value in strategy_diag_capability.scopes
    assert ToolScope.MCP_ANALYTICS.value not in strategy_diag_capability.scopes
    assert strategy_global_okr_capability is not None
    assert strategy_global_okr_capability.domain == "strategy"
    assert "okrs.global.create" in strategy_global_okr_capability.permissions
    assert ToolScope.MCP_USER.value in strategy_global_okr_capability.scopes
    assert strategy_area_okr_capability is not None
    assert strategy_area_okr_capability.domain == "strategy"
    assert "okrs.area.create" in strategy_area_okr_capability.permissions
    assert ToolScope.MCP_ADMIN.value in strategy_area_okr_capability.scopes
    assert strategy_global_kr_capability is not None
    assert strategy_global_kr_capability.domain == "strategy"
    assert "okrs.key_results.create" in strategy_global_kr_capability.permissions
    assert ToolScope.MCP_USER.value in strategy_global_kr_capability.scopes
    assert strategy_area_kr_capability is not None
    assert strategy_area_kr_capability.domain == "strategy"
    assert "okrs.key_results.create" in strategy_area_kr_capability.permissions


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
    assert "create_global_okr" in user_tool_names
    assert "create_area_okr" in user_tool_names
    assert "create_global_key_result" in user_tool_names
    assert "create_area_key_result" in user_tool_names
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
    assert "delete_meeting_secure" in admin_tool_names
    assert "delete_meeting_secure" not in user_tool_names


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
