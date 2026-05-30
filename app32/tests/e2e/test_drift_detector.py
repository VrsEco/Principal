from __future__ import annotations

from app32.tests.e2e.catalog.drift_detector import detect_inventory_drift, routes_compatible


def test_drift_detector_returns_payload():
    payload = detect_inventory_drift()

    assert "inventory_routes_total" in payload
    assert "status" in payload


def test_routes_compatible_handles_parameterized_and_concrete_paths():
    assert routes_compatible("/financial/reports/<report_slug>", "/financial/reports/agendamento")
    assert routes_compatible("/api/companies/<company_id>/processes", "/api/companies/<int:company_id>/processes")
