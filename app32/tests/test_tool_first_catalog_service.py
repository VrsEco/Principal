import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.tool_first_catalog_service import ToolFirstCatalogService


def test_tool_first_catalog_service_exposes_expected_summary():
    payload = ToolFirstCatalogService.build_catalog(None)

    assert payload["summary"]["domains"] >= 7
    assert payload["summary"]["canonical_domains"] >= 2
    assert payload["discovery"]["rest_endpoint"] == "/api/configs/ai/mcp/tool-first-catalog"
    assert payload["discovery"]["mcp_tool"] == "list_app32_capabilities"


def test_tool_first_catalog_service_filters_by_domain_status_and_surface():
    payload = ToolFirstCatalogService.build_catalog(
        None,
        domain="engineering",
        status="canonical",
        surface="engineering",
        include_backlog=False,
    )

    assert payload["filters"]["domain"] == ["engineering"]
    assert payload["filters"]["status"] == ["canonical"]
    assert payload["filters"]["surface"] == ["engineering"]
    assert payload["filters"]["include_backlog"] is False
    assert len(payload["domains"]) == 1
    assert payload["domains"][0]["key"] == "engineering"
    assert payload["domains"][0]["planned_tools"] == []
    published_names = {tool["name"] for tool in payload["domains"][0]["published_tools"]}
    assert "request_engineering_suggestion" in published_names
    assert "list_my_engineering_suggestions" in published_names


def test_tool_first_catalog_service_accepts_multiple_filter_values():
    payload = ToolFirstCatalogService.build_catalog(
        None,
        domain=["engineering", "strategy"],
        status=["canonical", "wrapper"],
        surface=["engineering", "sapiens"],
    )

    keys = {domain["key"] for domain in payload["domains"]}
    assert "engineering" in keys
    assert "strategy" in keys


def test_tool_first_catalog_service_engineering_governance_mentions_formal_backlog():
    payload = ToolFirstCatalogService.build_catalog(None, domain="engineering")

    engineering = payload["domains"][0]
    assert any("AA.J.1" in item for item in engineering["governance"])
