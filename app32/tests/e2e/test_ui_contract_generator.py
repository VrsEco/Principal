from __future__ import annotations

from app32.tests.e2e.catalog.ui_contract_generator import build_ui_human_like_contracts


def test_ui_contract_generator_builds_contracts_for_discovered_elements():
    payload = build_ui_human_like_contracts()

    assert payload["contracts_total"] > 0
    assert payload["contracts_total"] == payload["elements_total"]
    assert payload["risk_counts"]
    assert payload["priority_counts"]
    assert payload["execution_strategy_counts"]


def test_ui_contract_generator_classifies_rollback_and_company_scope():
    payload = build_ui_human_like_contracts()

    assert payload["rollback_required_total"] >= 0
    assert payload["company_id_required_total"] >= payload["human_gate_required_total"]
    assert all(item["requires_human_gate"] for item in payload["p0_contracts"])
