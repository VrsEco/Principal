from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, Iterable, Optional


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
TITLE_SETTLEMENT_STATE_VALUES = ("open", "partial", "settled")
TITLE_OPEN_BALANCE_STATES = frozenset({"open", "partial"})
TITLE_ENTERS_TRANSACTIONAL_VIEWS = frozenset({"open", "partial", "settled", "forecast"})
FINANCIAL_CONTRACT_VERSION = "financial_contract_v2"
SETTLEMENT_CORRECTION_COMPONENT_TYPES = frozenset({"monetary_correction", "interest", "fine", "manual_adjustment"})

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


def _money_float(value: Any) -> float:
    try:
        amount = Decimal(str(value or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except Exception:
        amount = Decimal("0.00")
    return float(amount)


def _extract_schedule_id_from_reference(external_reference: Any) -> Optional[int]:
    text = str(external_reference or "").strip()
    if not text.startswith("financial_schedule:"):
        return None
    raw_id = text.split(":", 1)[1].strip()
    if not raw_id.isdigit():
        return None
    return int(raw_id)


def resolve_title_settlement_state(
    *,
    principal_amount: Any = None,
    principal_settled: Any = None,
    adjustments_settled: Any = None,
    discounts_applied: Any = None,
    total_open: Any = None,
) -> str:
    principal_amount_decimal = Decimal(str(_money_float(principal_amount)))
    principal_settled_decimal = Decimal(str(_money_float(principal_settled)))
    adjustments_settled_decimal = Decimal(str(_money_float(adjustments_settled)))
    discounts_applied_decimal = Decimal(str(_money_float(discounts_applied)))
    total_open_decimal = Decimal(str(_money_float(total_open)))

    if total_open_decimal <= Decimal("0.00"):
        return "settled"

    settled_activity = principal_settled_decimal + adjustments_settled_decimal + discounts_applied_decimal
    if settled_activity > Decimal("0.00"):
        return "partial"

    if principal_amount_decimal <= Decimal("0.00") and total_open_decimal <= Decimal("0.00"):
        return "settled"

    return "open"


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


def title_state_has_open_balance(state: Optional[str]) -> bool:
    return _normalized(state) in TITLE_OPEN_BALANCE_STATES


def title_state_enters_transactional_views(state: Optional[str]) -> bool:
    return _normalized(state) in TITLE_ENTERS_TRANSACTIONAL_VIEWS


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


def build_financial_title_contract_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    contract = dict(payload or {})
    summary = dict(contract.get("summary") or {})
    financial_title_id = contract.get("financial_title_id") or contract.get("id")
    financial_title_code = contract.get("financial_title_code") or contract.get("schedule_code") or contract.get("display_code")
    financial_title_status = (
        summary.get("operational_state")
        or contract.get("operational_state")
        or contract.get("status")
    )
    financial_title_status_label = (
        summary.get("operational_state_label")
        or contract.get("operational_state_label")
        or title_operational_state_label(financial_title_status)
    )
    return {
        **contract,
        "contract_version": FINANCIAL_CONTRACT_VERSION,
        "entity_type": "financial_title",
        "entity_key": FINANCIAL_OPERATIONAL_GLOSSARY["schedule"]["canonical_key"],
        "entity_label": FINANCIAL_OPERATIONAL_GLOSSARY["schedule"]["singular"],
        "entity_legacy_label": FINANCIAL_OPERATIONAL_GLOSSARY["schedule"]["legacy_singular"],
        "financial_title_id": financial_title_id,
        "financial_title_code": financial_title_code,
        "title_id": financial_title_id,
        "title_code": financial_title_code,
        "financial_title_status": financial_title_status,
        "financial_title_status_label": financial_title_status_label,
    }


def _summarize_settlement_components(components: Iterable[Dict[str, Any]]) -> Dict[str, float]:
    totals: Dict[str, float] = {}
    for component in components:
        component_type = _normalized((component or {}).get("component_type"))
        if not component_type:
            continue
        totals[component_type] = _money_float(totals.get(component_type, 0) + _money_float((component or {}).get("amount")))
    correction_total = sum((Decimal(str(totals.get(component_type, 0))) for component_type in SETTLEMENT_CORRECTION_COMPONENT_TYPES), Decimal("0.00"))
    totals["financial_correction"] = _money_float(correction_total)
    return totals


def build_financial_settlement_contract_payload(
    payload: Dict[str, Any],
    *,
    entry_payload: Optional[Dict[str, Any]] = None,
    schedule_payload: Optional[Dict[str, Any]] = None,
    settlement_components: Optional[Iterable[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    contract = dict(payload or {})
    entry_data = dict(entry_payload or {})
    schedule_data = dict(schedule_payload or {})
    metadata = dict(contract.get("metadata_json") or {})
    title_snapshot = dict(metadata.get("financial_title_snapshot") or {})
    components = [dict(component or {}) for component in (settlement_components or contract.get("settlement_components") or [])]
    component_summary = _summarize_settlement_components(components)

    financial_title_id = (
        contract.get("financial_schedule_id")
        or entry_data.get("financial_schedule_id")
        or title_snapshot.get("financial_schedule_id")
        or schedule_data.get("id")
        or _extract_schedule_id_from_reference(contract.get("external_reference"))
    )
    financial_title_code = (
        contract.get("financial_title_code")
        or title_snapshot.get("schedule_code")
        or schedule_data.get("schedule_code")
        or entry_data.get("schedule_code")
    )
    financial_entry_code = entry_data.get("entry_code")
    financial_correction_amount = component_summary.get("financial_correction")
    if financial_correction_amount is None:
        financial_correction_amount = _money_float(
            _money_float(contract.get("interest_amount"))
            + _money_float(contract.get("penalty_amount"))
            + _money_float(contract.get("fee_amount"))
            + _money_float(contract.get("other_adjustments_amount"))
        )
    total_amount = contract.get("gross_amount")
    if total_amount is None:
        total_amount = contract.get("net_amount")

    return {
        **contract,
        "contract_version": FINANCIAL_CONTRACT_VERSION,
        "entity_type": "settlement",
        "entity_key": FINANCIAL_OPERATIONAL_GLOSSARY["settlement"]["canonical_key"],
        "entity_label": FINANCIAL_OPERATIONAL_GLOSSARY["settlement"]["singular"],
        "entity_legacy_label": FINANCIAL_OPERATIONAL_GLOSSARY["settlement"]["legacy_singular"],
        "financial_settlement_id": contract.get("id"),
        "financial_settlement_code": contract.get("settlement_code"),
        "settlement_id": contract.get("id"),
        "financial_title_id": financial_title_id,
        "financial_title_code": financial_title_code,
        "financial_entry_code": financial_entry_code,
        "financial_correction_amount": _money_float(financial_correction_amount),
        "total_amount": _money_float(total_amount),
        "settlement_components": components,
        "settlement_component_summary": component_summary,
        "financial_title_snapshot": title_snapshot or None,
    }
