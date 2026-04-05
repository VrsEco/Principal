from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any, Optional

from models import db
from models.agent_action_backlog_link import AgentActionBacklogLink
from models.project import ProjectTask
from services.agent_backlog_service import (
    DEFAULT_AGENT_BACKLOG_PROJECT_CODE,
    create_backlog_task,
)
from services.project_task_service import ProjectTaskService

logger = logging.getLogger(__name__)


SUPPORTED_AGENT_ACTION_TYPES = {
    "workflow_approval_request",
    "approval_request",
    "technical_fix",
}

ACTION_TYPE_PREFIX = {
    "workflow_approval_request": "[HITL][Workflow]",
    "approval_request": "[HITL][Aprovação]",
    "technical_fix": "[ENG][Correção]",
}

ACTION_PRIORITY = {
    "workflow_approval_request": "high",
    "approval_request": "high",
    "technical_fix": "high",
}


def _normalize_text(value: Any) -> str:
    return str(value or "").strip()


def _truncate(value: str, max_length: int = 200) -> str:
    normalized = _normalize_text(value)
    if len(normalized) <= max_length:
        return normalized
    return normalized[: max_length - 3].rstrip() + "..."


def _get_action_payload(action: Any) -> dict[str, Any]:
    return dict(getattr(action, "payload", None) or {})


def _is_supported_action(action: Any) -> bool:
    return _normalize_text(getattr(action, "type", None)) in SUPPORTED_AGENT_ACTION_TYPES


def _build_backlog_title(action: Any) -> str:
    action_type = _normalize_text(getattr(action, "type", None))
    prefix = ACTION_TYPE_PREFIX.get(action_type, "[AgentAction]")
    base_title = _normalize_text(getattr(action, "title", None)) or f"AgentAction #{getattr(action, 'id', 'N/A')}"
    return _truncate(f"{prefix} {base_title}", 200)


def _build_backlog_metadata(action: Any) -> dict[str, Any]:
    payload = _get_action_payload(action)
    metadata = {
        "agent_action_id": getattr(action, "id", None),
        "agent_action_type": getattr(action, "type", None),
        "agent_action_status": getattr(action, "status", None),
        "requesting_agent": getattr(action, "requesting_agent", None),
        "handling_agent": getattr(action, "handling_agent", None),
        "created_at": getattr(action, "created_at", None).isoformat()
        if getattr(action, "created_at", None)
        else None,
        "approval_key": payload.get("approval_key"),
        "action_key": payload.get("action_key"),
        "channel": payload.get("channel"),
        "object_code": payload.get("object_code"),
        "approval_status": payload.get("approval_status"),
    }
    return {key: value for key, value in metadata.items() if value not in (None, "", [], {})}


def _build_link_note(action: Any) -> str:
    payload = _get_action_payload(action)
    return "\n".join(
        [
            f"AgentAction vinculado: #{getattr(action, 'id', 'N/A')}",
            f"Tipo do AgentAction: {_normalize_text(getattr(action, 'type', None)) or 'N/A'}",
            f"Status inicial do AgentAction: {_normalize_text(getattr(action, 'status', None)) or 'N/A'}",
            f"Requesting agent: {_normalize_text(getattr(action, 'requesting_agent', None)) or 'N/A'}",
            f"Handling agent: {_normalize_text(getattr(action, 'handling_agent', None)) or 'N/A'}",
            f"approval_key: {_normalize_text(payload.get('approval_key')) or 'N/A'}",
            f"action_key: {_normalize_text(payload.get('action_key')) or 'N/A'}",
            f"channel: {_normalize_text(payload.get('channel')) or 'N/A'}",
            f"object_code: {_normalize_text(payload.get('object_code')) or 'N/A'}",
        ]
    ).strip()


def _append_notes_once(existing_notes: Optional[str], block: str) -> str:
    current = _normalize_text(existing_notes)
    normalized_block = _normalize_text(block)
    if not normalized_block:
        return current
    if normalized_block in current:
        return current
    if not current:
        return normalized_block
    return f"{current}\n\n{normalized_block}"


def _effective_action_status(action: Any) -> str:
    status = _normalize_text(getattr(action, "status", None)).lower() or "pending"
    payload = _get_action_payload(action)
    approval_status = _normalize_text(payload.get("approval_status")).lower()
    if status == "pending" and approval_status == "expired":
        return "expired"
    if status == "pending" and approval_status in {"approved", "rejected"}:
        return approval_status
    return status


def _resolve_completion_date(action: Any) -> date:
    resolved_at = getattr(action, "resolved_at", None)
    if hasattr(resolved_at, "date"):
        return resolved_at.date()

    executed_at = getattr(action, "executed_at", None)
    if hasattr(executed_at, "date"):
        return executed_at.date()

    return datetime.utcnow().date()


def _resolve_backlog_task_state(action: Any) -> tuple[str, str, Optional[date]]:
    effective_status = _effective_action_status(action)

    if effective_status in {"pending", "awaiting_approval", "expired"}:
        return "planned", "waiting", None
    if effective_status == "approved":
        return "in_progress", "pending", None
    if effective_status == "executed":
        return "completed", "completed", _resolve_completion_date(action)
    if effective_status == "rejected":
        return "completed", "completed", _resolve_completion_date(action)
    if effective_status in {"failed", "rolled_back"}:
        return "cancelled", "suspended", None
    return "planned", "inbox", None


def _build_sync_key(action: Any) -> str:
    payload = _get_action_payload(action)
    return "|".join(
        [
            str(getattr(action, "id", "")),
            _effective_action_status(action),
            _normalize_text(payload.get("approval_status")).lower(),
        ]
    )


def _build_sync_log(action: Any) -> dict[str, Any]:
    payload = _get_action_payload(action)
    return {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "author": "agent_action_backlog_service",
        "type": "agent_action_sync",
        "action_id": getattr(action, "id", None),
        "action_type": getattr(action, "type", None),
        "action_status": getattr(action, "status", None),
        "approval_status": payload.get("approval_status"),
        "sync_key": _build_sync_key(action),
        "summary": (
            f"AgentAction #{getattr(action, 'id', 'N/A')} sincronizado: "
            f"status={_effective_action_status(action)}"
        ),
        "details": {
            "requesting_agent": getattr(action, "requesting_agent", None),
            "handling_agent": getattr(action, "handling_agent", None),
            "object_code": payload.get("object_code"),
            "channel": payload.get("channel"),
        },
    }


def _append_sync_log(task: Any, action: Any) -> None:
    logs = list(getattr(task, "logs", None) or [])
    new_log = _build_sync_log(action)
    sync_key = new_log["sync_key"]
    for item in reversed(logs):
        if not isinstance(item, dict):
            continue
        if item.get("type") == "agent_action_sync" and item.get("sync_key") == sync_key:
            return
    logs.append(new_log)
    task.logs = logs


def _ensure_payload_backlog_card(action: Any, task: Any, link: Any) -> None:
    payload = _get_action_payload(action)
    payload["backlog_card"] = {
        "task_id": getattr(task, "id", None),
        "task_code": getattr(task, "code", None),
        "project_code": getattr(link, "backlog_project_code", None)
        or DEFAULT_AGENT_BACKLOG_PROJECT_CODE,
        "link_type": getattr(link, "link_type", None),
    }
    action.payload = payload


def _recover_orphan_backlog_task_for_action(action: Any) -> Optional[ProjectTask]:
    project_id = ProjectTaskService.extract_id_from_code(DEFAULT_AGENT_BACKLOG_PROJECT_CODE)
    action_id = getattr(action, "id", None)
    if not project_id or not action_id:
        return None
    marker = f"agent_action_id: {action_id}"
    return (
        ProjectTask.query.filter(
            ProjectTask.project_id == project_id,
            ProjectTask.notes.contains(marker),
        )
        .order_by(ProjectTask.id.desc())
        .first()
    )


def find_backlog_link_by_action_id(action_id: Optional[int]) -> Optional[AgentActionBacklogLink]:
    if not action_id:
        return None
    return AgentActionBacklogLink.query.filter_by(agent_action_id=int(action_id)).first()


def _create_link_for_task(action: Any, task: Any) -> AgentActionBacklogLink:
    return AgentActionBacklogLink(
        company_id=int(getattr(action, "company_id", None) or 0),
        agent_action_id=int(getattr(action, "id", None)),
        project_task_id=int(getattr(task, "id", None)),
        link_type=_normalize_text(getattr(action, "type", None)) or "agent_action",
        backlog_project_code=DEFAULT_AGENT_BACKLOG_PROJECT_CODE,
    )


def _apply_action_state_to_task(task: Any, action: Any) -> None:
    status, stage, completion_date = _resolve_backlog_task_state(action)
    task.status = status
    task.stage = stage
    task.completion_date = completion_date
    task.notes = _append_notes_once(task.notes, _build_link_note(action))
    _append_sync_log(task, action)


def ensure_backlog_task_for_action(
    action: Any,
    *,
    autocommit: bool = True,
) -> tuple[Optional[AgentActionBacklogLink], Optional[Any]]:
    if action is None or not _is_supported_action(action):
        return None, None

    link = find_backlog_link_by_action_id(getattr(action, "id", None))
    if link and getattr(link, "task", None) is not None:
        _ensure_payload_backlog_card(action, link.task, link)
        _apply_action_state_to_task(link.task, action)
        if autocommit:
            db.session.commit()
        else:
            db.session.flush()
        return link, link.task

    task = _recover_orphan_backlog_task_for_action(action)
    if task is None:
        task, error = create_backlog_task(
            source_type=f"agent_action:{_normalize_text(getattr(action, 'type', None)) or 'unknown'}",
            title=_build_backlog_title(action),
            description=_normalize_text(getattr(action, "description", None))
            or "Sem descrição operacional informada.",
            user_id=getattr(action, "user_id", None),
            company_id=getattr(action, "company_id", None),
            metadata=_build_backlog_metadata(action),
            priority=ACTION_PRIORITY.get(
                _normalize_text(getattr(action, "type", None)),
                "high",
            ),
        )
        if error or task is None:
            logger.warning(
                "Nao foi possivel criar backlog para AgentAction #%s: %s",
                getattr(action, "id", None),
                error,
            )
            return None, None

    link = _create_link_for_task(action, task)
    db.session.add(link)
    _ensure_payload_backlog_card(action, task, link)
    _apply_action_state_to_task(task, action)

    if autocommit:
        db.session.commit()
    else:
        db.session.flush()
    return link, task


def sync_backlog_task_for_action(
    action: Any,
    *,
    autocommit: bool = False,
) -> Optional[Any]:
    if action is None or not _is_supported_action(action):
        return None

    link = find_backlog_link_by_action_id(getattr(action, "id", None))
    if link is None or getattr(link, "task", None) is None:
        link, task = ensure_backlog_task_for_action(action, autocommit=autocommit)
        return task

    task = link.task
    _ensure_payload_backlog_card(action, task, link)
    _apply_action_state_to_task(task, action)

    if autocommit:
        db.session.commit()
    else:
        db.session.flush()
    return task
