import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from financial_domain import (
    build_financial_settlement_contract_payload,
    build_financial_title_contract_payload,
    build_title_operational_state_metadata,
    resolve_title_operational_state,
    resolve_title_settlement_state,
    title_state_in_accounting_reports,
    title_state_has_open_balance,
    title_state_in_projected_reports,
)


def test_resolve_title_operational_state_prioritizes_forecast_when_entry_type_is_forecast():
    result = resolve_title_operational_state(
        schedule_status="active",
        settlement_state="open",
        entry_type="forecast",
        metadata_json={},
    )

    assert result == "forecast"


def test_resolve_title_operational_state_keeps_draft_and_cancelled_as_terminal_states():
    assert resolve_title_operational_state(schedule_status="draft", settlement_state="partial") == "draft"
    assert resolve_title_operational_state(schedule_status="cancelled", settlement_state="settled") == "cancelled"


def test_operational_state_metadata_marks_accounting_and_projected_inclusion():
    partial_state = build_title_operational_state_metadata(
        schedule_status="active",
        settlement_state="partial",
        entry_type="payable",
        metadata_json={},
    )
    forecast_state = build_title_operational_state_metadata(
        schedule_status="active",
        settlement_state="open",
        entry_type="forecast",
        metadata_json={"is_forecast": True},
    )

    assert partial_state["code"] == "partial"
    assert partial_state["label"] == "Parcial"
    assert partial_state["include_in_accounting_reports"] is True
    assert partial_state["include_in_projected_reports"] is False

    assert forecast_state["code"] == "forecast"
    assert forecast_state["label"] == "Projetado"
    assert forecast_state["include_in_accounting_reports"] is False
    assert forecast_state["include_in_projected_reports"] is True


def test_title_state_predicates_follow_canonical_rule():
    assert title_state_in_accounting_reports("open") is True
    assert title_state_in_accounting_reports("forecast") is False
    assert title_state_in_projected_reports("forecast") is True
    assert title_state_in_projected_reports("settled") is False
    assert title_state_has_open_balance("partial") is True
    assert title_state_has_open_balance("settled") is False


def test_resolve_title_settlement_state_marks_discounted_title_as_partial_until_zero_balance():
    assert resolve_title_settlement_state(
        principal_amount=1000,
        principal_settled=0,
        adjustments_settled=0,
        discounts_applied=100,
        total_open=900,
    ) == "partial"
    assert resolve_title_settlement_state(
        principal_amount=1000,
        principal_settled=1000,
        adjustments_settled=0,
        discounts_applied=0,
        total_open=0,
    ) == "settled"


def test_resolve_title_settlement_state_marks_principal_zero_as_settled_even_with_adjustment_open():
    assert resolve_title_settlement_state(
        principal_amount=1000,
        principal_settled=1000,
        adjustments_settled=0,
        discounts_applied=0,
        total_open=25,
    ) == "settled"


def test_build_financial_title_contract_payload_exposes_canonical_aliases():
    payload = build_financial_title_contract_payload(
        {
            "id": 15,
            "schedule_code": "TIT-000015",
            "status": "active",
            "summary": {
                "operational_state": "partial",
                "operational_state_label": "Parcial",
            },
        }
    )

    assert payload["contract_version"] == "financial_contract_v2"
    assert payload["entity_type"] == "financial_title"
    assert payload["financial_title_id"] == 15
    assert payload["financial_title_code"] == "TIT-000015"
    assert payload["financial_title_status"] == "partial"
    assert payload["financial_title_status_label"] == "Parcial"


def test_build_financial_settlement_contract_payload_links_title_and_correction_summary():
    payload = build_financial_settlement_contract_payload(
        {
            "id": 901,
            "settlement_code": "LIQ-000901",
            "financial_entry_id": 88,
            "external_reference": "financial_schedule:15",
            "gross_amount": 235,
            "interest_amount": 20,
            "penalty_amount": 5,
            "other_adjustments_amount": 10,
            "metadata_json": {
                "financial_title_snapshot": {
                    "financial_schedule_id": 15,
                    "schedule_code": "TIT-000015",
                }
            },
        },
        entry_payload={
            "id": 88,
            "entry_code": "LAN-000088",
            "financial_schedule_id": 15,
        },
        settlement_components=[
            {"component_type": "principal", "amount": 200},
            {"component_type": "interest", "amount": 20},
            {"component_type": "fine", "amount": 5},
            {"component_type": "manual_adjustment", "amount": 10},
        ],
    )

    assert payload["contract_version"] == "financial_contract_v2"
    assert payload["entity_type"] == "settlement"
    assert payload["financial_settlement_id"] == 901
    assert payload["financial_settlement_code"] == "LIQ-000901"
    assert payload["financial_title_id"] == 15
    assert payload["financial_title_code"] == "TIT-000015"
    assert payload["financial_entry_code"] == "LAN-000088"
    assert payload["financial_correction_amount"] == 35.0
    assert payload["total_amount"] == 235.0
    assert payload["settlement_component_summary"]["financial_correction"] == 35.0


def test_build_financial_settlement_contract_payload_uses_legacy_amounts_without_components():
    payload = build_financial_settlement_contract_payload(
        {
            "id": 902,
            "settlement_code": "LIQ-000902",
            "financial_entry_id": 89,
            "external_reference": "financial_schedule:16",
            "principal_amount": 100,
            "net_amount": 112,
            "interest_amount": 7,
            "penalty_amount": 3,
            "fee_amount": 2,
            "discount_amount": 5,
        },
        entry_payload={"id": 89, "entry_code": "LAN-000089", "financial_schedule_id": 16},
    )

    assert payload["financial_correction_amount"] == 12.0
    assert payload["settlement_component_summary"]["principal"] == 100.0
    assert payload["settlement_component_summary"]["financial_correction"] == 12.0
    assert payload["settlement_component_summary"]["discount"] == 5.0
    assert payload["total_amount"] == 112.0
