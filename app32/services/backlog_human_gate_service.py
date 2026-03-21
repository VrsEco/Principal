from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from models import db
from models.agent_action import AgentAction
from models.agent_action_backlog_link import AgentActionBacklogLink
from models.process import ProcessInstance
from models.project import ProjectTask
from services.agent_action_backlog_service import sync_backlog_task_for_action
from services.agent_backlog_service import DEFAULT_AGENT_BACKLOG_PROJECT_CODE
from services.project_task_service import ProjectTaskService
from services.workflow_approval_service import (
    WorkflowApprovalService,
    serialize_workflow_approval_action,
)

logger = logging.getLogger(__name__)

BACKLOG_HUMAN_GATE_TIMELINE_LIMIT = 12
BACKLOG_HUMAN_GATE_SLA_WARNING_HOURS = 24
BACKLOG_HUMAN_GATE_SLA_DANGER_HOURS = 48


@dataclass
class BacklogHumanGateOutcome:
    success: bool
    message: str
    http_status: int = 200
    action: Optional[Any] = None
    resume_payload: dict[str, Any] = field(default_factory=dict)
    resume_result: dict[str, Any] = field(default_factory=dict)
    audit_metadata: dict[str, Any] = field(default_factory=dict)


def _normalize_text(value: Any) -> str:
    return str(value or "").strip()


def _serialize_datetime(value: Any) -> Optional[str]:
    return value.isoformat() if hasattr(value, "isoformat") else value


def _serialize_jsonish(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _serialize_jsonish(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_serialize_jsonish(item) for item in value]
    return _serialize_datetime(value)


def _coerce_datetime(value: Any) -> Optional[datetime]:
    if value is None:
        return None

    parsed: Optional[datetime] = None
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            return None

    if parsed is None:
        return None

    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def _describe_age(delta_seconds: float) -> str:
    safe_seconds = max(int(delta_seconds or 0), 0)
    total_hours = safe_seconds // 3600
    days, hours = divmod(total_hours, 24)
    if days > 0:
        return f"{days}d {hours}h"
    if total_hours > 0:
        return f"{total_hours}h"
    minutes = max(safe_seconds // 60, 0)
    return f"{minutes}min"


def _effective_action_status(action: Any) -> str:
    payload = dict(getattr(action, "payload", None) or {})
    action_status = _normalize_text(getattr(action, "status", None)).lower() or "pending"
    approval_status = _normalize_text(payload.get("approval_status")).lower()

    if action_status == "pending" and approval_status == "expired":
        return "expired"
    if action_status == "pending" and approval_status in {"approved", "rejected"}:
        return approval_status
    return action_status


def _build_available_operations(action: Any) -> list[dict[str, str]]:
    action_type = _normalize_text(getattr(action, "type", None))
    effective_status = _effective_action_status(action)

    if action_type == "workflow_approval_request":
        if effective_status == "pending":
            return [
                {"id": "approve", "label": "Aprovar", "style": "primary"},
                {"id": "reject", "label": "Rejeitar", "style": "danger"},
                {"id": "revalidate", "label": "Renovar prazo", "style": "secondary"},
            ]
        if effective_status == "expired":
            return [{"id": "revalidate", "label": "Revalidar", "style": "primary"}]
        return []

    if action_type == "approval_request":
        if effective_status == "pending":
            return [
                {"id": "approve", "label": "Aprovar", "style": "primary"},
                {"id": "reject", "label": "Rejeitar", "style": "danger"},
            ]
        return []

    if action_type == "technical_fix":
        operations: list[dict[str, str]] = []
        if _normalize_text(getattr(action, "status", None)).lower() == "awaiting_approval":
            operations.append({"id": "approve", "label": "Aplicar hotfix", "style": "primary"})
        if (
            _normalize_text(getattr(action, "status", None)).lower() == "executed"
            and _normalize_text(getattr(action, "original_file", None))
            and getattr(action, "backup_content", None)
        ):
            operations.append({"id": "rollback", "label": "Rollback", "style": "warning"})
        return operations

    return []


def _operation_label(operation: Any) -> str:
    normalized_operation = _normalize_text(operation).lower()
    if normalized_operation == "approve":
        return "Aprovação"
    if normalized_operation == "reject":
        return "Rejeição"
    if normalized_operation == "revalidate":
        return "Revalidação"
    if normalized_operation == "rollback":
        return "Rollback"
    return _normalize_text(operation) or "Operação"


def _status_tone(status: Any) -> str:
    normalized_status = _normalize_text(status).lower()
    if normalized_status in {"executed", "approved"}:
        return "success"
    if normalized_status in {"rejected", "rolled_back"}:
        return "muted"
    if normalized_status in {"failed", "expired"}:
        return "danger"
    if normalized_status in {"pending", "awaiting_approval"}:
        return "warning"
    return "info"


def _append_backlog_operation_log(
    task: Any,
    *,
    action: Any,
    operation: str,
    actor_name: str,
    message: str,
    success: bool,
    feedback: Optional[str] = None,
    status_before: Optional[str] = None,
    status_after: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
) -> None:
    logs = list(getattr(task, "logs", None) or [])
    logs.append(
        {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "author": actor_name or "Operação",
            "type": "backlog_human_gate_operation",
            "action_id": getattr(action, "id", None),
            "action_type": getattr(action, "type", None),
            "operation": _normalize_text(operation).lower(),
            "operation_label": _operation_label(operation),
            "summary": _normalize_text(message) or "Operação HITL registrada no backlog.",
            "message": _normalize_text(message) or "Operação HITL registrada no backlog.",
            "success": bool(success),
            "status_before": _normalize_text(status_before).lower() or None,
            "status_after": _normalize_text(status_after).lower() or None,
            "feedback": _normalize_text(feedback) or None,
            "details": _serialize_jsonish(details or {}),
        }
    )
    task.logs = logs


def _build_timeline_entry(log_entry: dict[str, Any]) -> Optional[dict[str, Any]]:
    if not isinstance(log_entry, dict):
        return None

    entry_type = _normalize_text(log_entry.get("type")).lower()
    if entry_type == "backlog_human_gate_operation":
        status_after = _normalize_text(log_entry.get("status_after")).lower()
        tone = "danger" if not bool(log_entry.get("success", True)) else _status_tone(status_after or "executed")
        return {
            "type": entry_type,
            "timestamp": _serialize_datetime(log_entry.get("timestamp")),
            "author": log_entry.get("author"),
            "label": log_entry.get("operation_label") or _operation_label(log_entry.get("operation")),
            "summary": log_entry.get("summary") or log_entry.get("message"),
            "message": log_entry.get("message") or log_entry.get("summary"),
            "tone": tone,
            "success": bool(log_entry.get("success", True)),
            "operation": log_entry.get("operation"),
            "status_before": log_entry.get("status_before"),
            "status_after": log_entry.get("status_after"),
            "feedback": log_entry.get("feedback"),
            "details": _serialize_jsonish(log_entry.get("details") or {}),
        }

    if entry_type == "agent_action_sync":
        status = log_entry.get("approval_status") or log_entry.get("action_status")
        return {
            "type": entry_type,
            "timestamp": _serialize_datetime(log_entry.get("timestamp")),
            "author": log_entry.get("author"),
            "label": "Sincronização",
            "summary": log_entry.get("summary") or "Card sincronizado com AgentAction.",
            "message": log_entry.get("summary") or "Card sincronizado com AgentAction.",
            "tone": _status_tone(status),
            "success": True,
            "operation": None,
            "status_before": None,
            "status_after": _normalize_text(status).lower() or None,
            "feedback": None,
            "details": _serialize_jsonish(log_entry.get("details") or {}),
        }

    return None


def _build_backlog_human_gate_timeline(task: Any) -> list[dict[str, Any]]:
    logs = list(getattr(task, "logs", None) or [])
    timeline: list[dict[str, Any]] = []
    for item in reversed(logs):
        entry = _build_timeline_entry(item)
        if entry is None:
            continue
        timeline.append(entry)
        if len(timeline) >= BACKLOG_HUMAN_GATE_TIMELINE_LIMIT:
            break
    return timeline


def _build_operational_health(action: Any, timeline: list[dict[str, Any]]) -> dict[str, Any]:
    effective_status = _effective_action_status(action)
    action_type = _normalize_text(getattr(action, "type", None)).lower()
    reference_now = datetime.utcnow()
    created_at = _coerce_datetime(getattr(action, "created_at", None))
    last_event = timeline[0] if timeline else None
    last_event_failed = bool(last_event and last_event.get("success") is False)

    age_seconds: Optional[int] = None
    age_hours: Optional[int] = None
    age_label = "N/D"
    if created_at is not None:
        age_seconds = max(int((reference_now - created_at).total_seconds()), 0)
        age_hours = age_seconds // 3600
        age_label = _describe_age(age_seconds)

    if effective_status in {"executed", "approved"}:
        sla_bucket = "resolved"
        sla_label = "Fluxo atendido"
        sla_tone = "success"
    elif effective_status in {"rejected", "rolled_back"}:
        sla_bucket = "closed"
        sla_label = "Fluxo encerrado"
        sla_tone = "muted"
    elif effective_status in {"failed", "expired"}:
        sla_bucket = "breached"
        sla_label = "SLA crítico"
        sla_tone = "danger"
    elif age_hours is None:
        sla_bucket = "unknown"
        sla_label = "SLA sem base"
        sla_tone = "muted"
    elif age_hours >= BACKLOG_HUMAN_GATE_SLA_DANGER_HOURS:
        sla_bucket = "breached"
        sla_label = "SLA crítico"
        sla_tone = "danger"
    elif age_hours >= BACKLOG_HUMAN_GATE_SLA_WARNING_HOURS:
        sla_bucket = "warning"
        sla_label = "SLA em atenção"
        sla_tone = "warning"
    else:
        sla_bucket = "healthy"
        sla_label = "SLA saudável"
        sla_tone = "success"

    badges: list[dict[str, Any]] = []
    if last_event_failed or effective_status == "failed":
        badges.append({"id": "error_pending", "label": "Erro pendente", "tone": "danger"})

    if effective_status == "expired":
        badges.append({"id": "reprocess", "label": "Reprocesso", "tone": "warning"})

    if effective_status in {"pending", "awaiting_approval", "expired", "failed"} and sla_bucket in {"warning", "breached"}:
        badges.append({"id": "sla_attention", "label": "Atenção SLA", "tone": sla_tone})

    if action_type == "workflow_approval_request" and effective_status == "approved":
        badges.append({"id": "manual_followup", "label": "Acompanhamento", "tone": "info"})

    queue_bucket = "completed"
    if any(badge["id"] == "error_pending" for badge in badges):
        queue_bucket = "error_pending"
    elif any(badge["id"] == "reprocess" for badge in badges):
        queue_bucket = "reprocess"
    elif effective_status in {"pending", "awaiting_approval", "expired"}:
        queue_bucket = "pending"
    elif effective_status in {"rejected", "rolled_back"}:
        queue_bucket = "closed"

    return {
        "queue_bucket": queue_bucket,
        "age_hours": age_hours,
        "age_seconds": age_seconds,
        "age_label": age_label,
        "sla": {
            "bucket": sla_bucket,
            "label": sla_label,
            "tone": sla_tone,
        },
        "badges": badges,
        "requires_attention": any(badge["id"] in {"error_pending", "reprocess", "sla_attention"} for badge in badges),
        "requires_reprocess": any(badge["id"] == "reprocess" for badge in badges),
        "has_pending_error": any(badge["id"] == "error_pending" for badge in badges),
    }


def serialize_linked_agent_action(action: Any) -> dict[str, Any]:
    if action is None:
        return {}

    action_type = _normalize_text(getattr(action, "type", None))
    if action_type == "workflow_approval_request":
        serialized = serialize_workflow_approval_action(action)
        serialized["available_operations"] = _build_available_operations(action)
        return serialized

    payload = dict(getattr(action, "payload", None) or {})
    return {
        "id": getattr(action, "id", None),
        "type": getattr(action, "type", None),
        "status": getattr(action, "status", None),
        "effective_status": _effective_action_status(action),
        "title": getattr(action, "title", None),
        "description": getattr(action, "description", None),
        "company_id": getattr(action, "company_id", None),
        "user_id": getattr(action, "user_id", None),
        "requesting_agent": getattr(action, "requesting_agent", None),
        "handling_agent": getattr(action, "handling_agent", None),
        "created_at": _serialize_datetime(getattr(action, "created_at", None)),
        "resolved_at": _serialize_datetime(getattr(action, "resolved_at", None)),
        "executed_at": _serialize_datetime(getattr(action, "executed_at", None)),
        "payload_preview": {
            key: value
            for key, value in {
                "approval_status": payload.get("approval_status"),
                "task_type": payload.get("task_type"),
                "task_id": payload.get("task_id"),
                "new_deadline": payload.get("new_deadline"),
                "reason": payload.get("reason"),
                "requester": payload.get("requester"),
                "proposal": payload.get("proposal"),
                "backlog_card": payload.get("backlog_card"),
            }.items()
            if value not in (None, "", [], {})
        },
        "available_operations": _build_available_operations(action),
    }


def _build_context(*, task_id: int, project_id: int, link: Any, action: Any) -> dict[str, Any]:
    task = getattr(link, "task", None)
    timeline = _build_backlog_human_gate_timeline(task) if task is not None else []
    operational_health = _build_operational_health(action, timeline)
    return {
        "enabled": True,
        "task_id": task_id,
        "project_id": project_id,
        "project_code": getattr(link, "backlog_project_code", None) or DEFAULT_AGENT_BACKLOG_PROJECT_CODE,
        "agent_action_id": getattr(action, "id", None),
        "agent_action_type": getattr(action, "type", None),
        "agent_action_status": getattr(action, "status", None),
        "effective_status": _effective_action_status(action),
        "link_type": getattr(link, "link_type", None),
        "source_company_id": getattr(action, "company_id", None),
        "available_operations": _build_available_operations(action),
        "action": serialize_linked_agent_action(action),
        "timeline": timeline,
        "last_event": timeline[0] if timeline else None,
        "operational_health": operational_health,
    }


def build_backlog_human_gate_context(task: Any) -> Optional[dict[str, Any]]:
    if task is None:
        return None

    link = getattr(task, "agent_action_backlog_link", None)
    action = getattr(link, "action", None) if link is not None else None
    if link is None or action is None:
        return None

    return _build_context(
        task_id=int(getattr(task, "id", 0) or 0),
        project_id=int(getattr(task, "project_id", 0) or 0),
        link=link,
        action=action,
    )


def build_backlog_human_gate_context_map(task_ids: list[int] | tuple[int, ...]) -> dict[int, dict[str, Any]]:
    normalized_task_ids = [int(task_id) for task_id in task_ids if task_id]
    if not normalized_task_ids:
        return {}

    links = (
        AgentActionBacklogLink.query.filter(
            AgentActionBacklogLink.project_task_id.in_(normalized_task_ids)
        )
        .order_by(AgentActionBacklogLink.project_task_id.asc())
        .all()
    )

    context_map: dict[int, dict[str, Any]] = {}
    for link in links:
        action = getattr(link, "action", None)
        if action is None:
            continue
        context_map[int(link.project_task_id)] = _build_context(
            task_id=int(link.project_task_id),
            project_id=int(getattr(getattr(link, "task", None), "project_id", 0) or 0),
            link=link,
            action=action,
        )
    return context_map


def find_backlog_link_by_task_id(task_id: Optional[int]) -> Optional[AgentActionBacklogLink]:
    if not task_id:
        return None
    return AgentActionBacklogLink.query.filter_by(project_task_id=int(task_id)).first()


def _build_audit_metadata(*, task: Any, link: Any, action: Any, operation: str) -> dict[str, Any]:
    return {
        "backlog_human_gate": {
            "operation": _normalize_text(operation).lower(),
            "task_id": getattr(task, "id", None),
            "task_code": getattr(task, "code", None),
            "project_id": getattr(task, "project_id", None),
            "backlog_project_code": getattr(link, "backlog_project_code", None),
            "agent_action_id": getattr(action, "id", None),
            "agent_action_type": getattr(action, "type", None),
            "source_company_id": getattr(action, "company_id", None),
            "operated_via": "project_backlog_card",
        }
    }


def _merge_audit_metadata(base: Optional[dict[str, Any]], extra: Optional[dict[str, Any]]) -> dict[str, Any]:
    merged = dict(base or {})
    for key, value in dict(extra or {}).items():
        if key not in merged:
            merged[key] = value
            continue
        if isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = {**merged[key], **value}
            continue
        merged[key] = value
    return merged


def _record_backlog_operation_result(
    *,
    task: Any,
    action: Any,
    operation: str,
    actor_name: str,
    message: str,
    success: bool,
    feedback: Optional[str] = None,
    status_before: Optional[str] = None,
    status_after: Optional[str] = None,
    audit_metadata: Optional[dict[str, Any]] = None,
    resume_payload: Optional[dict[str, Any]] = None,
    resume_result: Optional[dict[str, Any]] = None,
) -> None:
    _append_backlog_operation_log(
        task,
        action=action,
        operation=operation,
        actor_name=actor_name,
        message=message,
        success=success,
        feedback=feedback,
        status_before=status_before,
        status_after=status_after,
        details={
            "audit_metadata": audit_metadata or {},
            "resume_payload": resume_payload or {},
            "resume_result": resume_result or {},
        },
    )


def _append_target_task_log(task: Any, *, actor_name: str, summary: str, details: dict[str, Any]) -> None:
    logs = list(getattr(task, "logs", None) or [])
    logs.append(
        {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "author": actor_name or "Operação",
            "type": "deadline_extension_approval",
            "summary": summary,
            "details": details,
        }
    )
    task.logs = logs


def _append_notes(existing_notes: Any, block: str) -> str:
    current = _normalize_text(existing_notes)
    normalized_block = _normalize_text(block)
    if not normalized_block:
        return current
    if not current:
        return normalized_block
    return f"{current}\n\n{normalized_block}"


def _log_workflow_approval_message_if_possible(action: Any, message: str, metadata: dict[str, Any]) -> None:
    try:
        from api.routes.agents import _log_workflow_approval_message as route_message_logger

        route_message_logger(action, message, metadata)
    except Exception:
        logger.exception(
            "Falha ao registrar mensagem operacional do workflow approval action_id=%s",
            getattr(action, "id", None),
        )


def _approve_legacy_deadline_extension(
    *,
    action: Any,
    task: Any,
    link: Any,
    actor_user_id: int,
    actor_name: str,
) -> BacklogHumanGateOutcome:
    if action is None:
        return BacklogHumanGateOutcome(success=False, message="Ação não encontrada.", http_status=404)

    status_before = _effective_action_status(action)
    if _normalize_text(getattr(action, "status", None)).lower() != "pending":
        return BacklogHumanGateOutcome(
            success=True,
            message=f"Ação já estava em status {_normalize_text(getattr(action, 'status', None)) or 'desconhecido'}.",
            action=action,
        )

    payload = dict(getattr(action, "payload", None) or {})
    task_type = _normalize_text(payload.get("task_type")).lower()
    target_id = int(payload.get("task_id") or 0)
    parsed_deadline, deadline_error = ProjectTaskService.parse_due_date(payload.get("new_deadline"))

    if deadline_error:
        return BacklogHumanGateOutcome(success=False, message=deadline_error, http_status=400, action=action)

    if parsed_deadline is None:
        return BacklogHumanGateOutcome(
            success=False,
            message="Solicitação sem nova data válida para aplicar.",
            http_status=400,
            action=action,
        )

    now = datetime.utcnow()
    audit_metadata = _build_audit_metadata(task=task, link=link, action=action, operation="approve")

    if task_type == "project_task":
        target_task = ProjectTask.query.get(target_id)
        if target_task is None:
            return BacklogHumanGateOutcome(
                success=False,
                message="Atividade alvo da solicitação de prazo não foi encontrada.",
                http_status=404,
                action=action,
            )
        project = getattr(target_task, "project", None)
        if project is None or int(getattr(project, "company_id", 0) or 0) != int(getattr(action, "company_id", 0) or 0):
            return BacklogHumanGateOutcome(
                success=False,
                message="A atividade alvo não pertence à empresa original da solicitação.",
                http_status=403,
                action=action,
            )
        previous_due_date = _serialize_datetime(getattr(target_task, "due_date", None))
        target_task.due_date = parsed_deadline
        _append_target_task_log(
            target_task,
            actor_name=actor_name,
            summary="Prazo alterado por aprovação HITL do backlog.",
            details={
                "previous_due_date": previous_due_date,
                "new_due_date": parsed_deadline.isoformat(),
                "agent_action_id": getattr(action, "id", None),
                "requester": payload.get("requester"),
                "reason": payload.get("reason"),
            },
        )
    elif task_type == "process_instance":
        target_instance = ProcessInstance.query.filter_by(
            id=target_id,
            company_id=int(getattr(action, "company_id", 0) or 0),
        ).first()
        if target_instance is None:
            return BacklogHumanGateOutcome(
                success=False,
                message="Instância de processo alvo da solicitação de prazo não foi encontrada.",
                http_status=404,
                action=action,
            )
        previous_due_date = _serialize_datetime(getattr(target_instance, "due_date", None))
        target_instance.due_date = parsed_deadline
        target_instance.notes = _append_notes(
            getattr(target_instance, "notes", None),
            "\n".join(
                [
                    f"Prazo aprovado via backlog operacional em {now.isoformat()}Z",
                    f"AgentAction: #{getattr(action, 'id', 'N/A')}",
                    f"Prazo anterior: {previous_due_date or 'N/A'}",
                    f"Novo prazo: {parsed_deadline.isoformat()}",
                    f"Aprovado por: {actor_name or 'Operação'}",
                    f"Motivo original: {_normalize_text(payload.get('reason')) or 'N/A'}",
                ]
            ),
        )
    else:
        return BacklogHumanGateOutcome(
            success=False,
            message="Tipo de solicitação legado não suportado para execução pelo backlog.",
            http_status=400,
            action=action,
        )

    payload["approval_status"] = "approved"
    payload["approved_by_user_id"] = actor_user_id
    payload["approved_at"] = now.isoformat()
    payload["applied_new_deadline"] = parsed_deadline.isoformat()
    action.payload = payload
    action.status = "executed"
    action.user_feedback = f"Aprovado por {actor_name}"
    action.resolved_at = now
    action.executed_at = now
    sync_backlog_task_for_action(action)
    _record_backlog_operation_result(
        task=task,
        action=action,
        operation="approve",
        actor_name=actor_name,
        message="Solicitação de prazo aprovada e aplicada com sucesso.",
        success=True,
        status_before=status_before,
        status_after=_effective_action_status(action),
        audit_metadata=audit_metadata,
    )
    db.session.commit()

    return BacklogHumanGateOutcome(
        success=True,
        message="Solicitação de prazo aprovada e aplicada com sucesso.",
        http_status=200,
        action=action,
        audit_metadata=audit_metadata,
    )


def _reject_legacy_deadline_extension(
    *,
    action: Any,
    task: Any,
    link: Any,
    actor_user_id: int,
    actor_name: str,
    feedback: Optional[str] = None,
) -> BacklogHumanGateOutcome:
    if action is None:
        return BacklogHumanGateOutcome(success=False, message="Ação não encontrada.", http_status=404)

    status_before = _effective_action_status(action)
    if _normalize_text(getattr(action, "status", None)).lower() != "pending":
        return BacklogHumanGateOutcome(
            success=True,
            message=f"Ação já estava em status {_normalize_text(getattr(action, 'status', None)) or 'desconhecido'}.",
            action=action,
        )

    now = datetime.utcnow()
    payload = dict(getattr(action, "payload", None) or {})
    payload["approval_status"] = "rejected"
    payload["rejected_by_user_id"] = actor_user_id
    payload["rejected_at"] = now.isoformat()
    if feedback:
        payload["rejection_feedback"] = feedback

    action.payload = payload
    action.status = "rejected"
    action.user_feedback = (
        f"Rejeitado por {actor_name}: {feedback}" if feedback else f"Rejeitado por {actor_name}"
    )
    action.resolved_at = now
    sync_backlog_task_for_action(action)
    audit_metadata = _build_audit_metadata(task=task, link=link, action=action, operation="reject")
    _record_backlog_operation_result(
        task=task,
        action=action,
        operation="reject",
        actor_name=actor_name,
        message="Solicitação de prazo rejeitada com sucesso.",
        success=True,
        feedback=feedback,
        status_before=status_before,
        status_after=_effective_action_status(action),
        audit_metadata=audit_metadata,
    )
    db.session.commit()

    return BacklogHumanGateOutcome(
        success=True,
        message="Solicitação de prazo rejeitada com sucesso.",
        http_status=200,
        action=action,
        audit_metadata=audit_metadata,
    )


def execute_backlog_human_gate_operation(
    *,
    task: Any,
    operation: str,
    actor_user_id: int,
    actor_name: str,
    feedback: Optional[str] = None,
) -> BacklogHumanGateOutcome:
    normalized_operation = _normalize_text(operation).lower()
    if normalized_operation not in {"approve", "reject", "revalidate", "rollback"}:
        return BacklogHumanGateOutcome(
            success=False,
            message="Operação do backlog inválida.",
            http_status=400,
        )

    link = find_backlog_link_by_task_id(getattr(task, "id", None))
    action = getattr(link, "action", None) if link is not None else None
    if link is None or action is None:
        return BacklogHumanGateOutcome(
            success=False,
            message="Card do backlog não possui AgentAction vinculado.",
            http_status=404,
        )

    expected_project_id = ProjectTaskService.extract_id_from_code(
        getattr(link, "backlog_project_code", None) or DEFAULT_AGENT_BACKLOG_PROJECT_CODE
    )
    task_project_id = int(getattr(task, "project_id", 0) or 0)
    if not expected_project_id or expected_project_id != task_project_id:
        return BacklogHumanGateOutcome(
            success=False,
            message="Card informado não pertence ao backlog operacional configurado.",
            http_status=403,
            action=action,
        )

    action_type = _normalize_text(getattr(action, "type", None))
    audit_metadata = _build_audit_metadata(
        task=task,
        link=link,
        action=action,
        operation=normalized_operation,
    )

    if action_type == "workflow_approval_request":
        from src.intelligence.menu_engine import execute_approved_resume_payload

        workflow_service = WorkflowApprovalService(resume_executor=execute_approved_resume_payload)
        status_before = _effective_action_status(action)

        if normalized_operation == "approve":
            outcome = workflow_service.approve(
                action=action,
                approver_user_id=actor_user_id,
                approver_name=actor_name,
                active_company_id=None,
            )
        elif normalized_operation == "reject":
            outcome = workflow_service.reject(
                action=action,
                approver_user_id=actor_user_id,
                approver_name=actor_name,
                active_company_id=None,
                feedback=feedback,
            )
        elif normalized_operation == "revalidate":
            outcome = workflow_service.revalidate(
                action=action,
                approver_user_id=actor_user_id,
                approver_name=actor_name,
                active_company_id=None,
            )
        else:
            return BacklogHumanGateOutcome(
                success=False,
                message="Workflow approval não suporta esta operação pelo backlog.",
                http_status=400,
                action=action,
            )

        if not outcome.success:
            db.session.rollback()
            fresh_task = ProjectTask.query.get(getattr(task, "id", None)) or task
            merged_audit = _merge_audit_metadata(outcome.audit_metadata, audit_metadata)
            _record_backlog_operation_result(
                task=fresh_task,
                action=action,
                operation=normalized_operation,
                actor_name=actor_name,
                message=outcome.message,
                success=False,
                feedback=feedback,
                status_before=status_before,
                status_after=_effective_action_status(action),
                audit_metadata=merged_audit,
                resume_payload=dict(outcome.resume_payload or {}),
                resume_result=dict(outcome.resume_result or {}),
            )
            db.session.commit()
            return BacklogHumanGateOutcome(
                success=False,
                message=outcome.message,
                http_status=outcome.http_status,
                action=action,
                resume_payload=dict(outcome.resume_payload or {}),
                resume_result=dict(outcome.resume_result or {}),
                audit_metadata=merged_audit,
            )

        merged_audit = _merge_audit_metadata(outcome.audit_metadata, audit_metadata)
        _log_workflow_approval_message_if_possible(action, outcome.message, merged_audit)
        _record_backlog_operation_result(
            task=task,
            action=action,
            operation=normalized_operation,
            actor_name=actor_name,
            message=outcome.message,
            success=True,
            feedback=feedback,
            status_before=status_before,
            status_after=_effective_action_status(action),
            audit_metadata=merged_audit,
            resume_payload=dict(outcome.resume_payload or {}),
            resume_result=dict(outcome.resume_result or {}),
        )
        db.session.commit()
        return BacklogHumanGateOutcome(
            success=True,
            message=outcome.message,
            http_status=outcome.http_status,
            action=action,
            resume_payload=dict(outcome.resume_payload or {}),
            resume_result=dict(outcome.resume_result or {}),
            audit_metadata=merged_audit,
        )

    if action_type == "approval_request":
        if normalized_operation == "approve":
            return _approve_legacy_deadline_extension(
                action=action,
                task=task,
                link=link,
                actor_user_id=actor_user_id,
                actor_name=actor_name,
            )
        if normalized_operation == "reject":
            return _reject_legacy_deadline_extension(
                action=action,
                task=task,
                link=link,
                actor_user_id=actor_user_id,
                actor_name=actor_name,
                feedback=feedback,
            )
        return BacklogHumanGateOutcome(
            success=False,
            message="Solicitação legada não suporta esta operação pelo backlog.",
            http_status=400,
            action=action,
        )

    if action_type == "technical_fix":
        from services.engineering_service import engineering_service

        status_before = _effective_action_status(action)
        if normalized_operation == "approve":
            success, message = engineering_service.execute_repair(getattr(action, "id", None))
            updated_action = AgentAction.query.get(getattr(action, "id", None)) or action
            sync_backlog_task_for_action(updated_action, autocommit=False)
            _record_backlog_operation_result(
                task=task,
                action=updated_action,
                operation="approve",
                actor_name=actor_name,
                message=message,
                success=bool(success),
                feedback=feedback,
                status_before=status_before,
                status_after=_effective_action_status(updated_action),
                audit_metadata=audit_metadata,
            )
            db.session.commit()
            return BacklogHumanGateOutcome(
                success=bool(success),
                message=message,
                http_status=200 if success else 500,
                action=updated_action,
                audit_metadata=audit_metadata,
            )

        if normalized_operation == "rollback":
            success, message = engineering_service.rollback_repair(getattr(action, "id", None))
            updated_action = AgentAction.query.get(getattr(action, "id", None)) or action
            sync_backlog_task_for_action(updated_action, autocommit=False)
            _record_backlog_operation_result(
                task=task,
                action=updated_action,
                operation="rollback",
                actor_name=actor_name,
                message=message,
                success=bool(success),
                feedback=feedback,
                status_before=status_before,
                status_after=_effective_action_status(updated_action),
                audit_metadata=audit_metadata,
            )
            db.session.commit()
            return BacklogHumanGateOutcome(
                success=bool(success),
                message=message,
                http_status=200 if success else 500,
                action=updated_action,
                audit_metadata=audit_metadata,
            )

        return BacklogHumanGateOutcome(
            success=False,
            message="Hotfix técnico não suporta esta operação pelo backlog.",
            http_status=400,
            action=action,
        )

    return BacklogHumanGateOutcome(
        success=False,
        message="Tipo de AgentAction ainda não suportado pelo backlog operacional.",
        http_status=400,
        action=action,
    )
