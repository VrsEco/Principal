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
        "get_commercial_product_service_readiness",
        "list_commercial_offer_process_candidates",
        "get_commercial_offer_contract_guidance",
        "update_commercial_offer_contract",
        "build_commercial_billing_review",
        "generate_commercial_billing_batch",
        "generate_commercial_financial_titles_for_billing",
        "export_commercial_fiscal_integration_spreadsheet",
    }.issubset(mcp.registered)


def test_commercial_offer_contract_write_requires_explicit_human_gate():
    mcp = _FakeMCP()
    register_commercial_mcp_tools(mcp)

    result = mcp.registered["update_commercial_offer_contract"](
        company_id=9,
        item_id=3,
        commercial_contract={},
        human_gate_confirmed=False,
    )

    assert result == {
        "success": False,
        "error": "Confirmação humana explícita é obrigatória para alterar o contrato operacional da oferta.",
    }


def test_tool_first_catalog_maps_commercial_finance_work_journey_and_mcp_governance():
    payload = ToolFirstCatalogService.build_catalog(None, include_backlog=False)
    domains = {domain["key"]: domain for domain in payload["domains"]}

    assert {
        "commercial_contracts",
        "finance",
        "work_journey",
        "mcp_governance",
    }.issubset(domains)
    commercial_tools = {tool["name"] for tool in domains["commercial_contracts"]["published_tools"]}
    assert "get_commercial_dashboard" in commercial_tools
    assert "get_commercial_product_service_readiness" in commercial_tools
    assert "list_commercial_offer_process_candidates" in commercial_tools
    assert "get_commercial_offer_contract_guidance" in commercial_tools
    assert "update_commercial_offer_contract" in commercial_tools
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
    assert catalog.get_tool_capability("update_commercial_offer_contract").human_gate is True


def test_crud_contracts_include_governance_for_commercial_contracts():
    manifest = build_app32_crud_contracts_manifest()
    governance = manifest.get_domain("governance")

    assert governance is not None
    assert any(operation.entity == "commercial_contract" for operation in governance.operations)
    assert {operation.action for operation in governance.operations} >= {"list", "read", "create", "update", "delete"}


def test_new_commercial_read_tools_redact_internal_failures(monkeypatch):
    import sys
    from types import SimpleNamespace
    from contextlib import nullcontext
    from services.contracts_catalog_service import ContractsCatalogService

    marker = 'postgresql://private-user:private-password@private-host/customer-data'

    def fail(*args, **kwargs):
        raise RuntimeError(marker)

    monkeypatch.setitem(sys.modules, 'app', SimpleNamespace(
        create_app=lambda: SimpleNamespace(app_context=lambda: nullcontext())))
    monkeypatch.setattr(ContractsCatalogService, 'list_commercial_offer_process_candidates', fail)
    monkeypatch.setattr(ContractsCatalogService, 'get_commercial_offer_contract_guidance', fail)
    mcp = _FakeMCP()
    register_commercial_mcp_tools(mcp)
    for name, args in [
        ('list_commercial_offer_process_candidates', {'company_id': 9}),
        ('get_commercial_offer_contract_guidance', {'company_id': 9, 'item_id': 3}),
    ]:
        result = mcp.registered[name](**args)
        assert result['success'] is False
        assert marker not in str(result)
        assert 'private-' not in str(result)
        assert result['error']
