import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from financial_domain import (
    build_title_operational_state_metadata,
    resolve_title_operational_state,
    title_state_in_accounting_reports,
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
