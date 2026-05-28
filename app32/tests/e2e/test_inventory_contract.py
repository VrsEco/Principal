from __future__ import annotations

from app32.tests.e2e.catalog.inventory import iter_inventory_items, load_inventory


def test_inventory_has_modules_and_smoke_minimum():
    data = load_inventory()
    assert data["version"] >= 1
    assert data["modules"]
    assert data["smoke_minimum"]["scenarios"]


def test_inventory_items_have_required_fields():
    items = iter_inventory_items()
    assert items
    for item in items:
        assert item["key"]
        assert item["route"]
        assert item["environment_modes"]
        assert item["actions"]
        assert item["scenario"]
