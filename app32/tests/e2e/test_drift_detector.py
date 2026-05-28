from __future__ import annotations

from app32.tests.e2e.catalog.drift_detector import detect_inventory_drift


def test_drift_detector_returns_payload():
    payload = detect_inventory_drift()

    assert "inventory_routes_total" in payload
    assert "status" in payload
