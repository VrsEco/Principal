from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any, Optional

from models.project import ProjectTask
from services.project_task_service import ProjectTaskService

logger = logging.getLogger(__name__)

DEFAULT_AGENT_BACKLOG_PROJECT_CODE = os.environ.get("AGENT_BACKLOG_PROJECT_CODE", "AA.J.31")
DEFAULT_ROBOT_FAILURE_PROJECT_CODE = os.environ.get("ROBOT_TEST_FAILURE_PROJECT_CODE", "AA.J.19")
DEFAULT_AGENT_BACKLOG_TASK_STAGE = os.environ.get("AGENT_BACKLOG_TASK_STAGE", "inbox")
DEFAULT_AGENT_BACKLOG_TASK_STATUS = os.environ.get("AGENT_BACKLOG_TASK_STATUS", "planned")
DEFAULT_AGENT_BACKLOG_TASK_PRIORITY = os.environ.get("AGENT_BACKLOG_TASK_PRIORITY", "high")


def _normalize_text(value: Any) -> str:
    return str(value or "").strip()


def _append_block(parts: list[str], label: str, value: Any) -> None:
    normalized = _normalize_text(value)
    if normalized:
        parts.append(f"{label}: {normalized}")


def _resolve_project_code(source_type: str, metadata: Optional[dict[str, Any]]) -> str:
    metadata_project_code = _normalize_text((metadata or {}).get("project_code"))
    if metadata_project_code:
        return metadata_project_code
    if _normalize_text(source_type) == "e2e_failure":
        return DEFAULT_ROBOT_FAILURE_PROJECT_CODE
    return DEFAULT_AGENT_BACKLOG_PROJECT_CODE


def _build_description(*, source_type: str, description: str, metadata: Optional[dict[str, Any]]) -> str:
    lines = [f"Origem do backlog: {source_type}"]
    if description:
        lines.append("")
        lines.append(description.strip())
    extra = dict(metadata or {})
    if extra:
        lines.append("")
        lines.append("Metadados:")
        for key, value in extra.items():
            if value is None:
                continue
            lines.append(f"- {key}: {value}")
    return "\n".join(lines).strip()


def _build_notes(*, source_type: str, company_id: Optional[int], user_id: Optional[int], metadata: Optional[dict[str, Any]]) -> str:
    parts: list[str] = [
        f"Criado automaticamente em {datetime.utcnow().isoformat()}Z",
        f"Tipo de origem: {source_type}",
    ]
    _append_block(parts, "Company ID", company_id)
    _append_block(parts, "User ID", user_id)
    for key, value in dict(metadata or {}).items():
        if value is None:
            continue
        if key in {"traceback"}:
            continue
        _append_block(parts, key, value)
    return "\n".join(parts).strip()


def create_backlog_task(
    *,
    source_type: str,
    title: str,
    description: str,
    user_id: Optional[int],
    company_id: Optional[int],
    metadata: Optional[dict[str, Any]] = None,
    priority: Optional[str] = None,
) -> tuple[Optional[ProjectTask], Optional[str]]:
    normalized_title = _normalize_text(title) or "Item de backlog do agente"
    project_code = _resolve_project_code(source_type, metadata)
    result, error = ProjectTaskService.create_project_task(
        project_code=project_code,
        task_name=normalized_title,
        user_id=int(user_id or 0),
        allowed_company_ids=None,
        responsible_name=None,
        due_date=None,
        description=_build_description(
            source_type=source_type,
            description=description,
            metadata=metadata,
        ),
        amount=None,
        status=DEFAULT_AGENT_BACKLOG_TASK_STATUS,
        stage=DEFAULT_AGENT_BACKLOG_TASK_STAGE,
        priority=(str(priority or DEFAULT_AGENT_BACKLOG_TASK_PRIORITY).strip() or DEFAULT_AGENT_BACKLOG_TASK_PRIORITY),
        notes=_build_notes(
            source_type=source_type,
            company_id=company_id,
            user_id=user_id,
            metadata=metadata,
        ),
    )
    if error:
        logger.warning("Nao foi possivel criar item de backlog %s no projeto %s: %s", source_type, project_code, error)
        return None, error
    if not result or not isinstance(result, dict):
        return None, "Resultado inválido ao criar item de backlog."
    task = result.get("task")
    if task is None:
        return None, "ProjectTaskService não retornou task."
    return task, None
