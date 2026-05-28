from __future__ import annotations

from app32.tests.e2e.catalog.inventory import iter_inventory_items
from app32.tests.e2e.config.smoke_targets import SMOKE_TARGETS


def test_smoke_targets_contract():
    inventory_by_key = {item["key"]: item for item in iter_inventory_items()}
    missing = [target.key for target in SMOKE_TARGETS if target.key not in inventory_by_key]
    assert not missing, f"Smoke targets ausentes no inventário: {missing}"

    for target in SMOKE_TARGETS:
        inventory_item = inventory_by_key[target.key]
        assert inventory_item["route"] == target.route
        assert target.expected_url_fragment
        assert target.readiness_selector
