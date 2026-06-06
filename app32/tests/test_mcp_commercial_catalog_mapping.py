from __future__ import annotations

from src.core.mcp_commercial_tools import register_commercial_mcp_tools
from src.intelligence.mcp_contracts.crud_domains import build_app32_crud_contracts_manifest
from src.intelligence.tool_catalog import catalog
from services.tool_first_catalog_service import ToolFirstCatalogService


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


def test_commercial_mcp_registrar_exposes_new_billing_and_dashboard_tools():
    mcp = _FakeMCP()
    register_commercial_mcp_tools(mcp)

    assert {
        "get_commercial_dashboard",
        "build_commercial_billing_review",
        "generate_commercial_billing_batch",
        "generate_commercial_financial_titles_for_billing",
        "export_commercial_fiscal_integration_spreadsheet",
    }.issubset(mcp.registered)


def test_tool_first_catalog_maps_commercial_finance_auctions_work_journey_and_mcp_governance():
    payload = ToolFirstCatalogService.build_catalog(None, include_backlog=False)
    domains = {domain["key"]: domain for domain in payload["domains"]}

    assert {
        "commercial_contracts",
        "finance",
        "real_estate_auctions",
        "work_journey",
        "mcp_governance",
    }.issubset(domains)
    commercial_tools = {tool["name"] for tool in domains["commercial_contracts"]["published_tools"]}
    assert "get_commercial_dashboard" in commercial_tools
    assert "generate_commercial_financial_titles_for_billing" in commercial_tools
    assert domains["commercial_contracts"]["summary"]["published_mcp_tools"] >= 40


def test_previously_unmapped_shared_mcp_tools_now_have_capability_metadata():
    expected = {
        "list_feature_catalog": "governance",
        "describe_app32_permission_matrix_tool": "governance",
        "request_new_app32_integration": "operations",
        "get_incentive_indicators": "finance",
        "approve_work_journey_absence_request_tool": "routine",
        "delete_work_journey_rule_tool": "routine",
    }

    for tool_name, expected_domain in expected.items():
        capability = catalog.get_tool_capability(tool_name)
        assert capability is not None
        assert capability.domain == expected_domain

    assert catalog.get_tool_capability("approve_work_journey_absence_request_tool").human_gate is True
    assert catalog.get_tool_capability("delete_work_journey_rule_tool").human_gate is True


def test_crud_contracts_include_governance_for_commercial_contracts():
    manifest = build_app32_crud_contracts_manifest()
    governance = manifest.get_domain("governance")

    assert governance is not None
    assert any(operation.entity == "commercial_contract" for operation in governance.operations)
    assert {operation.action for operation in governance.operations} >= {"list", "read", "create", "update", "delete"}
