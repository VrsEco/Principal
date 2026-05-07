from __future__ import annotations

from typing import Any

from models import ProcessActivityExecutionContract
from services.process_execution_mode_service import normalize_contract_configs, normalize_execution_mode


def resolve_activity_execution_contract(
    *,
    company_id: int,
    process_id: int,
    bpmn_element_id: str | None = None,
    process_routine_id: int | None = None,
) -> ProcessActivityExecutionContract | None:
    query = (
        ProcessActivityExecutionContract.query
        .filter_by(company_id=company_id, process_id=process_id, is_active=True)
    )
    if process_routine_id:
        query = query.filter(
            (ProcessActivityExecutionContract.process_routine_id == process_routine_id)
            | (ProcessActivityExecutionContract.bpmn_element_id == bpmn_element_id)
        )
    elif bpmn_element_id:
        query = query.filter_by(bpmn_element_id=bpmn_element_id)
    else:
        return None

    return query.order_by(
        ProcessActivityExecutionContract.version.desc(),
        ProcessActivityExecutionContract.updated_at.desc(),
        ProcessActivityExecutionContract.id.desc(),
    ).first()


def apply_contract_defaults(payload: dict[str, Any], contract: ProcessActivityExecutionContract | None) -> dict[str, Any]:
    payload = dict(payload or {})
    if contract:
        payload.setdefault("execution_mode", contract.execution_mode)
        payload.setdefault("interaction_mode", contract.interaction_mode)
        payload.setdefault("capability_key", contract.capability_key)
        payload.setdefault("handler_key", contract.auto_service_key)
        payload.setdefault("ai_config_json", contract.ai_config_json or {})
        payload.setdefault("metadata_json", {})
        payload["metadata_json"] = {
            **(payload.get("metadata_json") or {}),
            "contract_id": contract.id,
            "route_name": contract.route_name,
            "requires_human_gate": bool(contract.requires_human_gate),
            "allows_pause": bool(contract.allows_pause),
            "allows_retry": bool(contract.allows_retry),
            "sla_minutes": contract.sla_minutes,
            "ui_schema_json": contract.ui_schema_json or {},
            "rest_config_json": contract.rest_config_json or {},
            "mcp_config_json": contract.mcp_config_json or {},
            "ai_config_json": contract.ai_config_json or {},
            "completion_rules_json": contract.completion_rules_json or {},
        }

    return normalize_contract_configs(payload)
