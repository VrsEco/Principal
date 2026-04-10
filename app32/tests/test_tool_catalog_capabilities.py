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

    assert capability is not None
    assert capability.domain == "analytics"
    assert capability.risk == ToolRiskLevel.HIGH
    assert ToolScope.MCP_ANALYTICS.value in capability.scopes
    assert ToolScope.MCP_ADMIN.value not in capability.scopes
    assert capability.human_gate is True


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
    assert "list_my_companies" in admin_tool_names
    assert "list_my_companies" in user_tool_names


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
