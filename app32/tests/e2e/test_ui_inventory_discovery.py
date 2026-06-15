from __future__ import annotations

from app32.tests.e2e.catalog.ui_inventory_discovery import discover_template_routes, discover_ui_inventory


def test_ui_inventory_discovers_templates_and_elements():
    payload = discover_ui_inventory()

    assert payload["screens_total"] > 0
    assert payload["elements_total"] > 0
    assert payload["fields_total"] >= 0
    assert payload["buttons_total"] >= 0
    assert payload["links_total"] >= 0
    assert isinstance(payload["missing_contract_screens"], list)


def test_ui_inventory_maps_some_templates_to_routes():
    mapping = discover_template_routes()

    assert mapping
    assert any(routes for routes in mapping.values())
