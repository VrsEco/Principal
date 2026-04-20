from __future__ import annotations

from typing import Any, Dict, Optional


TITLE_OPERATIONAL_STATE_VALUES = (
    "draft",
    "forecast",
    "open",
    "partial",
    "settled",
    "cancelled",
)

TITLE_OPERATIONAL_STATE_LABELS = {
    "draft": "Rascunho",
    "forecast": "Projetado",
    "open": "Em aberto",
    "partial": "Parcial",
    "settled": "Liquidado",
    "cancelled": "Cancelado",
}

TITLE_ACCOUNTING_REPORT_INCLUDED_STATES = frozenset({"open", "partial", "settled"})
TITLE_PROJECTED_REPORT_INCLUDED_STATES = frozenset({"forecast"})
TITLE_ADJUSTMENT_OPEN_STATUSES = frozenset({"open", "partial"})

FINANCIAL_OPERATIONAL_GLOSSARY = {
    "schedule": {
        "technical_key": "financial_schedule",
        "canonical_key": "financial_title",
        "singular": "Título Financeiro",
        "plural": "Títulos Financeiros",
        "legacy_singular": "Agendamento",
        "legacy_plural": "Agendamentos",
    },
    "settlement": {
        "technical_key": "financial_settlement",
        "canonical_key": "settlement",
        "singular": "Baixa",
        "plural": "Baixas",
        "legacy_singular": "Liquidação",
        "legacy_plural": "Liquidações",
    },
}


def _normalized(value: Any) -> str:
    return str(value or "").strip().lower()


def is_forecast_title(*, entry_type: Optional[str] = None, metadata_json: Optional[Dict[str, Any]] = None) -> bool:
    metadata = dict(metadata_json or {})
    normalized_entry_type = _normalized(entry_type)
    if normalized_entry_type == "forecast":
        return True
    metadata_state = _normalized(metadata.get("operational_state"))
    if metadata_state == "forecast":
        return True
    return bool(metadata.get("is_forecast"))


def resolve_title_operational_state(
    *,
    schedule_status: Optional[str],
    settlement_state: Optional[str] = None,
    entry_type: Optional[str] = None,
    metadata_json: Optional[Dict[str, Any]] = None,
) -> str:
    normalized_schedule_status = _normalized(schedule_status)
    normalized_settlement_state = _normalized(settlement_state)

    if normalized_schedule_status in {"draft", "cancelled"}:
        return normalized_schedule_status
    if is_forecast_title(entry_type=entry_type, metadata_json=metadata_json):
        return "forecast"
    if normalized_settlement_state in {"open", "partial", "settled"}:
        return normalized_settlement_state
    if normalized_schedule_status == "completed":
        return "settled"
    return "open"


def title_operational_state_label(state: Optional[str]) -> str:
    normalized_state = resolve_title_operational_state(schedule_status=state) if _normalized(state) not in TITLE_OPERATIONAL_STATE_LABELS else _normalized(state)
    return TITLE_OPERATIONAL_STATE_LABELS.get(normalized_state, normalized_state or "Em aberto")


def title_state_in_accounting_reports(state: Optional[str]) -> bool:
    return _normalized(state) in TITLE_ACCOUNTING_REPORT_INCLUDED_STATES


def title_state_in_projected_reports(state: Optional[str]) -> bool:
    return _normalized(state) in TITLE_PROJECTED_REPORT_INCLUDED_STATES


def build_title_operational_state_metadata(
    *,
    schedule_status: Optional[str],
    settlement_state: Optional[str] = None,
    entry_type: Optional[str] = None,
    metadata_json: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    state = resolve_title_operational_state(
        schedule_status=schedule_status,
        settlement_state=settlement_state,
        entry_type=entry_type,
        metadata_json=metadata_json,
    )
    return {
        "code": state,
        "label": title_operational_state_label(state),
        "include_in_accounting_reports": title_state_in_accounting_reports(state),
        "include_in_projected_reports": title_state_in_projected_reports(state),
    }


def build_financial_glossary_payload() -> Dict[str, Any]:
    return {
        "schedule": dict(FINANCIAL_OPERATIONAL_GLOSSARY["schedule"]),
        "settlement": dict(FINANCIAL_OPERATIONAL_GLOSSARY["settlement"]),
        "title_operational_states": [
            {
                "code": state,
                "label": TITLE_OPERATIONAL_STATE_LABELS[state],
                "include_in_accounting_reports": state in TITLE_ACCOUNTING_REPORT_INCLUDED_STATES,
                "include_in_projected_reports": state in TITLE_PROJECTED_REPORT_INCLUDED_STATES,
            }
            for state in TITLE_OPERATIONAL_STATE_VALUES
        ],
    }
