from __future__ import annotations

from datetime import datetime
from collections import defaultdict
from typing import Any, Dict, Iterable, Optional

from models import db
from models.agent_menu import AgentMenuOption, AgentMenuSession
from models.workflow_usage import WorkflowExecutionLog

TERMINAL_STATUSES = {"completed", "cancelled", "failed", "approval_pending"}


def _normalize_text(value: Any) -> Optional[str]:
    text = str(value or "").strip()
    return text or None


def _safe_int(value: Any) -> Optional[int]:
    try:
        if value in (None, ""):
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _truncate_text(value: Any, limit: int = 1000) -> Optional[str]:
    text = _normalize_text(value)
    if text is None:
        return None
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _extract_menu_engine_metadata(metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    return dict((metadata or {}).get("menu_engine") or {})


def _extract_discovery_metadata(metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    return dict((metadata or {}).get("workflow_discovery") or {})


def _infer_route_source(discovery: Dict[str, Any]) -> Optional[str]:
    strategy = _normalize_text(discovery.get("strategy"))
    if strategy == "explicit_code":
        return "explicit_code"
    top_matches = discovery.get("top_matches") or []
    if top_matches and isinstance(top_matches, list):
        first = top_matches[0] if top_matches else {}
        if isinstance(first, dict):
            reasons = [str(item or "").strip().lower() for item in first.get("reasons") or []]
            if any(reason.startswith("explicit:") for reason in reasons):
                return "explicit_code"
            if any("semantic" in reason for reason in reasons):
                return "semantic"
            if any("keyword" in reason or "lexical" in reason for reason in reasons):
                return "lexical"
    return strategy


def _infer_status(
    *,
    menu_engine: Dict[str, Any],
    metadata: Optional[Dict[str, Any]],
    response_text: Optional[str],
) -> str:
    approval = dict((metadata or {}).get("workflow_approval") or {})
    if approval.get("required") and str(approval.get("status") or "").strip().lower() == "pending":
        return "approval_pending"

    intercept_stage = str(menu_engine.get("intercept_stage") or "").strip().lower()
    session_status = str(menu_engine.get("session_status") or "").strip().lower()
    response = str(response_text or "").strip().lower()

    if "cancelada" in response or "cancelled" in response:
        return "cancelled"
    if intercept_stage in {"awaiting_confirmation"} or session_status == "awaiting_confirmation":
        return "awaiting_confirmation"
    if intercept_stage.startswith("awaiting_") or session_status.startswith("awaiting_"):
        return "collecting_parameters"
    if intercept_stage.startswith("implicit_discovery") or intercept_stage == "explicit_code":
        if session_status == "idle":
            return "completed"
        return "selected"
    if session_status == "idle":
        return "completed"
    return "selected"


def _build_metadata_snapshot(
    *,
    metadata: Optional[Dict[str, Any]],
    request_text: Optional[str],
    response_text: Optional[str],
) -> Dict[str, Any]:
    snapshot = dict(metadata or {})
    snapshot["audit"] = {
        "request_text": _truncate_text(request_text, 500),
        "response_text": _truncate_text(response_text, 500),
    }
    return snapshot


def _resolve_option(
    *,
    company_id: Optional[int],
    workflow_code: Optional[str],
    action_key: Optional[str],
) -> Optional[AgentMenuOption]:
    normalized_code = _normalize_text(workflow_code)
    normalized_action = _normalize_text(action_key)

    if normalized_code:
        query = AgentMenuOption.query.filter_by(code=normalized_code, is_active=True)
        if company_id is not None:
            scoped = query.filter_by(company_id=company_id).first()
            if scoped is not None:
                return scoped
        global_option = query.filter_by(company_id=None).first()
        if global_option is not None:
            return global_option

    if normalized_action:
        query = AgentMenuOption.query.filter_by(action_key=normalized_action, is_active=True)
        if company_id is not None:
            scoped = query.filter_by(company_id=company_id).order_by(AgentMenuOption.sort_order.asc()).first()
            if scoped is not None:
                return scoped
        return query.filter_by(company_id=None).order_by(AgentMenuOption.sort_order.asc()).first()
    return None


def _find_existing_usage_log(
    *,
    session_id: Optional[int],
    user_id: Optional[int],
    channel: Optional[str],
    thread_id: Optional[str],
    workflow_code: str,
    action_key: Optional[str],
) -> Optional[WorkflowExecutionLog]:
    if session_id is not None:
        candidate = (
            WorkflowExecutionLog.query.filter_by(
                session_id=session_id,
                workflow_code=workflow_code,
            )
            .order_by(WorkflowExecutionLog.created_at.desc())
            .first()
        )
        if candidate is not None and (
            getattr(candidate, 'completed_at', None) is None
            and str(getattr(candidate, 'status', '') or '').strip().lower() not in TERMINAL_STATUSES
        ):
            return candidate
        return None

    query = WorkflowExecutionLog.query.filter_by(
        user_id=user_id,
        channel=channel,
        thread_id=thread_id,
        workflow_code=workflow_code,
    )
    if action_key:
        query = query.filter_by(action_key=action_key)
    candidate = query.order_by(WorkflowExecutionLog.created_at.desc()).first()
    if candidate is not None and (
        getattr(candidate, 'completed_at', None) is None
        and str(getattr(candidate, 'status', '') or '').strip().lower() not in TERMINAL_STATUSES
    ):
        return candidate
    return None


def record_workflow_usage_event(
    *,
    user_id: Optional[int],
    company_id: Optional[int],
    channel: str,
    thread_id: Optional[str],
    request_text: Optional[str],
    response_text: Optional[str],
    menu_metadata: Optional[Dict[str, Any]],
) -> Optional[WorkflowExecutionLog]:
    metadata = dict(menu_metadata or {})
    menu_engine = _extract_menu_engine_metadata(metadata)
    discovery = _extract_discovery_metadata(metadata)

    workflow_code = _normalize_text(menu_engine.get("selected_option_code") or discovery.get("selected_code"))
    action_key = _normalize_text(menu_engine.get("selected_action_key") or discovery.get("selected_action_key"))
    if not workflow_code and not action_key:
        return None

    intercept_stage = _normalize_text(menu_engine.get("intercept_stage"))
    if intercept_stage in {"root_menu", "explicit_code_not_found", "implicit_discovery_ambiguous", "implicit_discovery_no_match"}:
        return None

    option = _resolve_option(company_id=company_id, workflow_code=workflow_code, action_key=action_key)
    if option is not None:
        workflow_code = workflow_code or _normalize_text(option.code)
        action_key = action_key or _normalize_text(option.action_key)

    if not workflow_code:
        return None

    session_id = _safe_int(menu_engine.get("session_id"))
    existing = _find_existing_usage_log(
        session_id=session_id,
        user_id=user_id,
        channel=_normalize_text(channel) or "web",
        thread_id=_normalize_text(thread_id),
        workflow_code=workflow_code,
        action_key=action_key,
    )

    status = _infer_status(menu_engine=menu_engine, metadata=metadata, response_text=response_text)
    now = datetime.utcnow()
    metadata_snapshot = _build_metadata_snapshot(
        metadata=metadata,
        request_text=request_text,
        response_text=response_text,
    )

    is_new = existing is None
    log = existing or WorkflowExecutionLog(
        company_id=company_id,
        user_id=user_id,
        session_id=session_id,
        workflow_option_id=getattr(option, "id", None),
        workflow_code=workflow_code,
        action_key=action_key,
        channel=_normalize_text(channel) or "web",
        thread_id=_normalize_text(thread_id),
    )

    if is_new:
        log.route_source = _infer_route_source(discovery)
        log.interaction_count = 1
    else:
        log.interaction_count = int(log.interaction_count or 0) + 1

    log.company_id = company_id
    log.user_id = user_id
    log.session_id = session_id
    log.workflow_option_id = getattr(option, "id", None) or log.workflow_option_id
    log.workflow_code = workflow_code
    log.action_key = action_key
    log.channel = _normalize_text(channel) or "web"
    log.thread_id = _normalize_text(thread_id)
    log.route_source = log.route_source or _infer_route_source(discovery)
    log.intercept_stage = intercept_stage
    log.status = status
    log.confidence_route = _normalize_text((discovery.get("confidence") or {}).get("route"))
    log.request_text = _truncate_text(request_text, 2000)
    log.response_text = _truncate_text(response_text, 2000)
    log.metadata_json = metadata_snapshot
    log.updated_at = now
    if is_new:
        log.created_at = now
    if status in TERMINAL_STATUSES:
        log.completed_at = now

    if is_new:
        db.session.add(log)
        if option is not None:
            option.usage_count = int(option.usage_count or 0) + 1
            option.last_used_at = now
    elif option is not None and log.completed_at:
        option.last_used_at = now

    db.session.commit()
    return log


def serialize_workflow_execution_log(item: Any) -> Dict[str, Any]:
    metadata = dict(getattr(item, "metadata_json", None) or {})
    return {
        "id": getattr(item, "id", None),
        "company_id": getattr(item, "company_id", None),
        "user_id": getattr(item, "user_id", None),
        "session_id": getattr(item, "session_id", None),
        "workflow_option_id": getattr(item, "workflow_option_id", None),
        "workflow_code": getattr(item, "workflow_code", None),
        "action_key": getattr(item, "action_key", None),
        "channel": getattr(item, "channel", None),
        "thread_id": getattr(item, "thread_id", None),
        "route_source": getattr(item, "route_source", None),
        "intercept_stage": getattr(item, "intercept_stage", None),
        "status": getattr(item, "status", None),
        "confidence_route": getattr(item, "confidence_route", None),
        "interaction_count": getattr(item, "interaction_count", None),
        "request_text": getattr(item, "request_text", None),
        "response_text": getattr(item, "response_text", None),
        "metadata": metadata,
        "created_at": getattr(item, "created_at", None).isoformat() if getattr(item, "created_at", None) else None,
        "updated_at": getattr(item, "updated_at", None).isoformat() if getattr(item, "updated_at", None) else None,
        "completed_at": getattr(item, "completed_at", None).isoformat() if getattr(item, "completed_at", None) else None,
    }


def _sorted_dimension_rows(label: str, values: Dict[str, int]) -> list[Dict[str, Any]]:
    return [
        {label: key, "count": value}
        for key, value in sorted(values.items(), key=lambda item: (-item[1], item[0]))
    ]



def build_workflow_usage_metrics(items: Iterable[Any]) -> Dict[str, Any]:
    items = list(items or [])
    by_action: Dict[str, int] = {}
    by_channel: Dict[str, int] = {}
    by_status: Dict[str, int] = {}
    by_route_source: Dict[str, int] = {}
    by_confidence_route: Dict[str, int] = {}
    by_user: Dict[str, Dict[str, Any]] = {}
    by_company: Dict[str, Dict[str, Any]] = {}
    by_day: Dict[str, int] = defaultdict(int)

    for item in items:
        action_key = _normalize_text(getattr(item, "action_key", None)) or "(sem_action_key)"
        channel = _normalize_text(getattr(item, "channel", None)) or "(sem_canal)"
        status = _normalize_text(getattr(item, "status", None)) or "(sem_status)"
        route_source = _normalize_text(getattr(item, "route_source", None)) or "(sem_origem)"
        confidence_route = _normalize_text(getattr(item, "confidence_route", None)) or "(sem_confidence_route)"
        user_id = getattr(item, "user_id", None)
        company_id = getattr(item, "company_id", None)
        created_at = getattr(item, "created_at", None) or getattr(item, "updated_at", None)

        by_action[action_key] = by_action.get(action_key, 0) + 1
        by_channel[channel] = by_channel.get(channel, 0) + 1
        by_status[status] = by_status.get(status, 0) + 1
        by_route_source[route_source] = by_route_source.get(route_source, 0) + 1
        by_confidence_route[confidence_route] = by_confidence_route.get(confidence_route, 0) + 1

        user_key = str(user_id) if user_id is not None else "(sem_usuario)"
        user_row = by_user.setdefault(user_key, {"user_id": user_id, "count": 0, "channels": set(), "statuses": set()})
        user_row["count"] += 1
        user_row["channels"].add(channel)
        user_row["statuses"].add(status)

        company_key = str(company_id) if company_id is not None else "(sem_empresa)"
        company_row = by_company.setdefault(company_key, {"company_id": company_id, "count": 0, "action_keys": set(), "channels": set()})
        company_row["count"] += 1
        company_row["action_keys"].add(action_key)
        company_row["channels"].add(channel)

        if created_at is not None:
            by_day[str(created_at.date())] += 1

    return {
        "total": len(items),
        "by_action_key": _sorted_dimension_rows("action_key", by_action),
        "by_channel": _sorted_dimension_rows("channel", by_channel),
        "by_status": _sorted_dimension_rows("status", by_status),
        "by_route_source": _sorted_dimension_rows("route_source", by_route_source),
        "by_confidence_route": _sorted_dimension_rows("confidence_route", by_confidence_route),
        "by_user": [
            {
                "user_id": row["user_id"],
                "count": row["count"],
                "channels": sorted(row["channels"]),
                "statuses": sorted(row["statuses"]),
            }
            for row in sorted(by_user.values(), key=lambda item: (-item["count"], str(item["user_id"])))
        ],
        "by_company": [
            {
                "company_id": row["company_id"],
                "count": row["count"],
                "action_keys": sorted(row["action_keys"]),
                "channels": sorted(row["channels"]),
            }
            for row in sorted(by_company.values(), key=lambda item: (-item["count"], str(item["company_id"])))
        ],
        "by_day": _sorted_dimension_rows("date", dict(by_day)),
    }
