from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

from src.intelligence.tooling.capabilities import TOOL_CONTEXT_COMPANY

from flask import has_app_context
from langchain_core.messages import ToolMessage

from src.intelligence.audit import build_ai_execution_audit_record, emit_ai_execution_audit_event
from src.intelligence.security.tool_policy import ToolPolicyRequest, evaluate_tool_policy
from src.intelligence.tool_catalog import catalog
from src.intelligence.tool_context import get_sapiens_context

logger = logging.getLogger(__name__)

_ACTION_PREFIXES = {
    "list_": "read",
    "get_": "read",
    "read_": "read",
    "query_": "read",
    "search_": "discover",
    "find_": "discover",
    "analyze_": "analyze",
    "inspect_": "read",
    "create_": "create",
    "update_": "update",
    "delete_": "delete",
    "approve_": "approve",
    "complete_": "update",
    "finish_": "update",
    "send_": "create",
    "schedule_": "create",
    "start_": "create",
    "register_": "create",
}


def _infer_surface(role: str) -> str:
    normalized_role = str(role or "").strip().lower()
    if normalized_role in {"administrador_tecnico", "admin_tecnico"}:
        return "ops"
    if normalized_role == "administrador":
        return "admin"
    return "user"


def _infer_action(tool_name: str, capability: Any) -> str:
    if tool_name in {
        "delete_meeting_topic",
        "delete_meeting_decision",
        "delete_meeting_activity",
    }:
        return "update"
    for prefix, action in _ACTION_PREFIXES.items():
        if tool_name.startswith(prefix):
            return action
    tags = set(getattr(capability, "tags", ()) or ())
    if "mutation" in tags or "crud" in tags:
        return "update"
    return "read"


def _normalize_optional_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.isdigit():
            return int(stripped)
    return None


def _company_candidates_from_metadata(metadata: Any) -> list[int]:
    if not isinstance(metadata, dict):
        return []

    candidates: list[int] = []

    def _append(candidate: Any) -> None:
        normalized = _normalize_optional_int(candidate)
        if normalized is not None and normalized not in candidates:
            candidates.append(normalized)

    security = metadata.get("security") if isinstance(metadata.get("security"), dict) else {}
    session_data = metadata.get("session") if isinstance(metadata.get("session"), dict) else {}
    workflow_data = metadata.get("workflow") if isinstance(metadata.get("workflow"), dict) else {}
    payload_data = workflow_data.get("payload") if isinstance(workflow_data.get("payload"), dict) else {}

    for source in (
        metadata.get("company_id"),
        metadata.get("active_company_id"),
        metadata.get("selected_company_id"),
        metadata.get("pinned_company_id"),
        security.get("company_id"),
        security.get("active_company_id"),
        session_data.get("company_id"),
        session_data.get("active_company_id"),
        session_data.get("selected_company_id"),
        session_data.get("pinned_company_id"),
        workflow_data.get("company_id"),
        workflow_data.get("active_company_id"),
        workflow_data.get("selected_company_id"),
        workflow_data.get("pinned_company_id"),
        payload_data.get("_selected_company_id"),
        payload_data.get("_summary_company_id"),
    ):
        _append(source)

    return candidates


def _resolve_company_for_tool_call(tool_name: str, args: dict[str, Any], identity: Any) -> tuple[int | None, str | None]:
    explicit_company_id = _normalize_optional_int(args.get("company_id"))
    if explicit_company_id is not None:
        return explicit_company_id, "tool_args.company_id"

    if _normalize_optional_int(getattr(identity, "company_id", None)) is not None:
        return _normalize_optional_int(getattr(identity, "company_id", None)), "identity.company_id"

    metadata_candidates = _company_candidates_from_metadata(getattr(identity, "metadata", None))
    if metadata_candidates:
        return metadata_candidates[0], "metadata.company_id"

    metadata = getattr(identity, "metadata", None) or {}
    security = metadata.get("security", {}) if isinstance(metadata, dict) else {}
    accessible_company_ids = []
    for item in tuple(security.get("accessible_company_ids") or ()):
        normalized = _normalize_optional_int(item)
        if normalized is not None and normalized not in accessible_company_ids:
            accessible_company_ids.append(normalized)
    if len(accessible_company_ids) == 1:
        return accessible_company_ids[0], "security.single_accessible_company_id"

    return None, None


def resolve_state_tool_context(state: dict[str, Any]) -> dict[str, Any]:
    messages = state.get("messages") or []
    if not messages:
        return state

    last_message = messages[-1]
    tool_calls = getattr(last_message, "tool_calls", None) or []
    if not tool_calls:
        return state

    identity = get_sapiens_context()
    resolved_company_id = _normalize_optional_int(state.get("company_id"))
    resolution_source: str | None = None

    for tool_call in tool_calls:
        tool_name = str(tool_call.get("name") or "").strip()
        capability = catalog.get_tool_capability(tool_name)
        required_context = tuple(getattr(capability, "required_context", ()) or ())
        if TOOL_CONTEXT_COMPANY not in required_context:
            continue

        args = tool_call.get("args") if isinstance(tool_call.get("args"), dict) else {}
        if not isinstance(args, dict):
            args = {}
            tool_call["args"] = args

        candidate_company_id, candidate_source = _resolve_company_for_tool_call(tool_name, args, identity)
        if candidate_company_id is None:
            continue

        if _normalize_optional_int(args.get("company_id")) is None:
            args["company_id"] = candidate_company_id
        if resolved_company_id is None:
            resolved_company_id = candidate_company_id
            resolution_source = candidate_source

    if resolved_company_id is None:
        return state

    state["company_id"] = resolved_company_id
    if resolution_source:
        context_data = dict(state.get("context_data") or {})
        context_data.setdefault("tool_context_resolution", {})["company_id_source"] = resolution_source
        state["context_data"] = context_data
    return state


def _build_policy_request(tool_name: str, args: dict[str, Any], identity: Any) -> ToolPolicyRequest:
    capability = catalog.get_tool_capability(tool_name)
    metadata = identity.metadata or {}
    security = metadata.get("security", {}) if isinstance(metadata, dict) else {}
    confirmations = metadata.get("tool_confirmations", {}) if isinstance(metadata, dict) else {}
    requested_company_id = args.get("company_id", identity.company_id)
    role = security.get("role") or "colaborador"
    return ToolPolicyRequest(
        tool_name=tool_name,
        surface=_infer_surface(role),
        domain=getattr(capability, "domain", None),
        action=_infer_action(tool_name, capability),
        risk=getattr(getattr(capability, "risk", None), "value", "medium"),
        requested_company_id=requested_company_id,
        accessible_company_ids=tuple(security.get("accessible_company_ids") or ()),
        required_permissions=tuple(getattr(capability, "permissions", ()) or ()),
        confirmed_mutation=bool(confirmations.get(tool_name) or confirmations.get("*")),
        required_context=tuple(getattr(capability, "required_context", ()) or ()),
        metadata={"tool_args_keys": sorted(str(key) for key in args.keys())},
    )


def _emit_policy_audit(decision, *, status: str) -> None:
    record = build_ai_execution_audit_record(
        event_type=f"sapiens.tool_policy.{status}",
        runtime="sapiens",
        status=status,
        domain=decision.request.domain,
        operation=decision.request.action,
        tool_name=decision.request.tool_name,
        scope=decision.resolved_surface,
        company_id=decision.resolved_company_id,
        user_id=decision.principal.user_id,
        thread_id=decision.principal.thread_id,
        metadata={
            "reason": decision.reason,
            "checks": list(decision.checks),
            "risk": decision.resolved_risk,
        },
    )
    emit_ai_execution_audit_event(record, logger=logger)


def _human_gate_reason(decision: Any) -> str:
    return str(decision.reason or "").strip().lower()


def _requires_human_gate_request(decision: Any, capability: Any) -> bool:
    if decision.allowed:
        return False
    reason = _human_gate_reason(decision)
    del capability
    return "confirmação explícita" in reason


def _build_human_gate_action_key(tool_name: str) -> str:
    return f"tool.{tool_name}"


def _build_human_gate_approval_key(tool_name: str, user_id: int | None, company_id: int | None, args: dict[str, Any]) -> str:
    args_digest = hashlib.sha256(
        json.dumps(args, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()[:16]
    return f"tool_human_gate|{tool_name}|{user_id or 0}|{company_id or 0}|{args_digest}"


def _ensure_tool_human_gate_request(*, decision: Any, args: dict[str, Any], identity: Any, capability: Any) -> dict[str, Any] | None:
    if not has_app_context():
        return None
    resolved_company_id = decision.resolved_company_id
    if resolved_company_id is None:
        return None

    from datetime import datetime, timedelta

    from models import db
    from models.agent_action import AgentAction
    from services.agent_action_backlog_service import ensure_backlog_task_for_action

    tool_name = decision.request.tool_name
    approval_key = _build_human_gate_approval_key(tool_name, identity.user_id, resolved_company_id, args)
    action_key = _build_human_gate_action_key(tool_name)
    pending_actions = (
        AgentAction.query.filter_by(
            type="workflow_approval_request",
            status="pending",
            company_id=resolved_company_id,
            user_id=identity.user_id,
        )
        .order_by(AgentAction.created_at.desc())
        .limit(20)
        .all()
    )
    for pending in pending_actions:
        payload = dict(getattr(pending, "payload", None) or {})
        if payload.get("approval_key") == approval_key and payload.get("action_key") == action_key:
            return {
                "approval_request_id": pending.id,
                "reused_existing": True,
                "approval_key": approval_key,
                "action_key": action_key,
            }

    security = ((identity.metadata or {}).get("security", {}) or {}) if isinstance(identity.metadata, dict) else {}
    action = AgentAction(
        type="workflow_approval_request",
        status="pending",
        requesting_agent="sapiens",
        handling_agent="operations",
        title=f"Aprovação necessária: tool {tool_name}",
        description=(
            f"Tool sensível bloqueada até aprovação humana.\n"
            f"Tool: {tool_name}\n"
            f"Usuário: {identity.user_id}\n"
            f"Empresa: {resolved_company_id}\n"
            f"Motivo: {decision.reason}\n"
            f"Args: {args}"
        ),
        payload={
            "approval_key": approval_key,
            "approval_status": "pending",
            "approval_expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat(),
            "action_key": action_key,
            "channel": identity.channel,
            "object_code": tool_name,
            "request_payload": {
                "tool_name": tool_name,
                "args": args,
                "company_id": resolved_company_id,
                "thread_id": identity.thread_id,
                "trace_id": ((identity.metadata or {}).get("trace_id") if isinstance(identity.metadata, dict) else None),
            },
            "resume_payload": {
                "tool_name": tool_name,
                "args": args,
                "company_id": resolved_company_id,
                "thread_id": identity.thread_id,
            },
            "created_via": "tool_runtime_guard",
            "human_gate_reason": getattr(capability, "human_gate_reason", None) or decision.reason,
            "required_permissions": list(getattr(capability, "permissions", ()) or ()),
            "risk": getattr(getattr(capability, "risk", None), "value", decision.resolved_risk),
            "role": security.get("role"),
        },
        company_id=resolved_company_id,
        user_id=identity.user_id,
    )
    db.session.add(action)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception("Falha ao registrar human gate da tool %s", tool_name)
        return None
    try:
        ensure_backlog_task_for_action(action, autocommit=True)
    except Exception:
        logger.exception("Falha ao espelhar human gate da tool %s no backlog", tool_name)

    return {
        "approval_request_id": action.id,
        "reused_existing": False,
        "approval_key": approval_key,
        "action_key": action_key,
    }


def _find_approved_tool_human_gate(*, tool_name: str, args: dict[str, Any], identity: Any) -> dict[str, Any] | None:
    if not has_app_context():
        return None
    resolved_company_id = args.get("company_id", identity.company_id)
    if resolved_company_id is None:
        return None

    from models.agent_action import AgentAction

    approval_key = _build_human_gate_approval_key(tool_name, identity.user_id, resolved_company_id, args)
    approved_actions = (
        AgentAction.query.filter(
            AgentAction.type == "workflow_approval_request",
            AgentAction.company_id == resolved_company_id,
            AgentAction.user_id == identity.user_id,
            AgentAction.status.in_(("approved", "executed")),
        )
        .order_by(AgentAction.resolved_at.desc(), AgentAction.id.desc())
        .limit(20)
        .all()
    )
    for action in approved_actions:
        payload = dict(getattr(action, "payload", None) or {})
        if payload.get("created_via") != "tool_runtime_guard":
            continue
        if payload.get("approval_key") != approval_key:
            continue
        return {
            "approval_request_id": action.id,
            "approval_key": approval_key,
            "status": action.status,
        }
    return None


def build_denied_tool_messages(state: dict[str, Any]) -> list[ToolMessage]:
    messages = state.get("messages") or []
    if not messages:
        return []

    last_message = messages[-1]
    tool_calls = getattr(last_message, "tool_calls", None) or []
    if not tool_calls:
        return []

    identity = get_sapiens_context()
    denied_messages: list[ToolMessage] = []

    for tool_call in tool_calls:
        tool_name = str(tool_call.get("name") or "").strip()
        args = tool_call.get("args") if isinstance(tool_call.get("args"), dict) else {}
        capability = catalog.get_tool_capability(tool_name)
        request = _build_policy_request(tool_name, args, identity)
        source = {
            "user_id": identity.user_id,
            "company_id": identity.company_id,
            "employee_id": security_employee_id(identity),
            "role": ((identity.metadata or {}).get("security", {}) or {}).get("role"),
            "channel": identity.channel,
            "thread_id": identity.thread_id,
            "permissions": ((identity.metadata or {}).get("security", {}) or {}).get("permissions", ()),
            "metadata": identity.metadata,
        }
        approved_human_gate = None
        if not request.confirmed_mutation:
            approved_human_gate = _find_approved_tool_human_gate(tool_name=tool_name, args=args, identity=identity)
            if approved_human_gate is not None:
                request = ToolPolicyRequest(
                    **{
                        **request.__dict__,
                        "confirmed_mutation": True,
                        "metadata": {
                            **dict(request.metadata or {}),
                            "approved_human_gate_request_id": approved_human_gate["approval_request_id"],
                        },
                    }
                )
        decision = evaluate_tool_policy(source, request)
        if decision.allowed:
            if approved_human_gate is not None:
                _emit_policy_audit(decision, status="resumed_after_human_gate")
            continue
        if _requires_human_gate_request(decision, capability):
            approval = _ensure_tool_human_gate_request(
                decision=decision,
                args=args,
                identity=identity,
                capability=capability,
            )
            if approval is not None:
                _emit_policy_audit(decision, status="human_gate_requested")
                denied_messages.append(
                    ToolMessage(
                        content=(
                            f"Execução pausada por governança. "
                            f"Solicitação de aprovação #{approval['approval_request_id']} "
                            f"{'reaproveitada' if approval['reused_existing'] else 'registrada'} "
                            f"para a tool {tool_name}."
                        ),
                        name=tool_name,
                        tool_call_id=str(tool_call.get("id") or tool_name),
                        status="error",
                        additional_kwargs={
                            "policy_decision": decision.to_audit_event(),
                            "workflow_approval": {
                                "required": True,
                                "status": "pending",
                                **approval,
                            },
                        },
                    )
                )
                continue
        _emit_policy_audit(decision, status="blocked")
        denied_messages.append(
            ToolMessage(
                content=f"Execução bloqueada pela governança: {decision.reason}.",
                name=tool_name,
                tool_call_id=str(tool_call.get("id") or tool_name),
                status="error",
                additional_kwargs={"policy_decision": decision.to_audit_event()},
            )
        )

    return denied_messages


def security_employee_id(identity: Any) -> int | None:
    metadata = identity.metadata or {}
    if not isinstance(metadata, dict):
        return None
    security = metadata.get("security", {})
    if not isinstance(security, dict):
        return None
    employee_id = security.get("employee_id")
    return int(employee_id) if isinstance(employee_id, int) else None
