from __future__ import annotations

from app32.tests.e2e.catalog.suite_catalog import get_suite_definition, list_suite_catalog


def test_suite_catalog_contains_supervised_entries():
    catalog = {item.suite_id: item for item in list_suite_catalog()}

    assert "smoke_real_navigation" in catalog
    assert "ui_inventory_contract_scan" in catalog
    assert "ui_human_like_contract_generation" in catalog
    assert "work_journey_manual_task_crud_devfull" in catalog
    assert "report_filter_volume_probe" in catalog
    assert "contracts_functional_probe" in catalog


def test_suite_catalog_resolves_suite():
    suite = get_suite_definition("mcp_concurrency_probe")

    assert suite.domain == "mcp"
    assert suite.command_kind == "python"
