from __future__ import annotations

import os
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from models.project import ProjectTask
from services.project_task_service import ProjectTaskService


class EngineeringSuggestionRequestPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str = Field(min_length=3, max_length=255)
    suggestion_type: str = Field(default="improvement", pattern="^(bug|improvement|observation)$")
    scope_label: str = Field(default="Operação Geral", min_length=3, max_length=120)
    objective: str = Field(min_length=10, max_length=3000)
    source_channel: str = Field(default="mcp", min_length=2, max_length=64)
    urgency: str = Field(default="medium", pattern="^(low|medium|high|critical)$")
    evidence_summary: str | None = Field(default=None, max_length=3000)
    notes: str | None = Field(default=None, max_length=3000)


class EngineeringSuggestionRequestService:
    BACKLOG_PROJECT_CODE = os.environ.get("ENGINEERING_REQUEST_PROJECT_CODE", "AA.J.1")
    SOURCE_MARKER = "source_channel=engineering_suggestion_mcp"
    TITLE_PREFIX = "[Sugestão Engenharia] "
    BACKLOG_STAGE_LABELS = {
        "inbox": "Caixa de Entrada",
        "waiting": "Aguardando",
        "executing": "Executando",
        "pending": "Pendências",
        "suspended": "Suspensos",
        "completed": "Concluídos",
    }
    SUGGESTION_TYPE_LABELS = {
        "bug": "Bug",
        "improvement": "Melhoria",
        "observation": "Observação",
    }

    @classmethod
    def _project_id(cls) -> int | None:
        project, error = ProjectTaskService.resolve_project_by_code(
            cls.BACKLOG_PROJECT_CODE,
            allowed_company_ids=None,
        )
        if error or project is None:
            return None
        return int(project.id)

    @classmethod
    def _extract_note_value(cls, notes: str, marker: str) -> str | None:
        prefix = f"{marker}="
        for line in (notes or "").splitlines():
            if line.startswith(prefix):
                return line[len(prefix):].strip() or None
        return None

    @classmethod
    def _serialize_task(cls, task: ProjectTask) -> dict[str, Any]:
        stage = str(getattr(task, "stage", None) or "inbox").strip().lower()
        notes = getattr(task, "notes", None) or ""
        raw_title = str(getattr(task, "what", "") or "").strip()
        title = raw_title.replace(cls.TITLE_PREFIX, "", 1) if raw_title.startswith(cls.TITLE_PREFIX) else raw_title
        suggestion_type = cls._extract_note_value(notes, "suggestion_type") or "improvement"
        requester_company_id = cls._extract_note_value(notes, "requester_company_id")
        return {
            "id": getattr(task, "id", None),
            "title": title,
            "suggestion_type": suggestion_type,
            "suggestion_type_label": cls.SUGGESTION_TYPE_LABELS.get(suggestion_type, suggestion_type),
            "scope_label": cls._extract_note_value(notes, "scope_label") or "Operação Geral",
            "source_channel": cls._extract_note_value(notes, "source_origin") or "mcp",
            "urgency": cls._extract_note_value(notes, "urgency") or "medium",
            "requester_company_id": int(requester_company_id) if requester_company_id and requester_company_id.isdigit() else None,
            "status": stage,
            "status_label": cls.BACKLOG_STAGE_LABELS.get(stage, stage or "-"),
            "backlog_task_id": getattr(task, "id", None),
            "backlog_task_code": getattr(task, "code", None),
            "created_at": getattr(task, "created_at", None).isoformat() if getattr(task, "created_at", None) else None,
            "updated_at": getattr(task, "updated_at", None).isoformat() if getattr(task, "updated_at", None) else None,
        }

    @classmethod
    def list_requests(
        cls,
        *,
        company_id: int | None,
        requester_user_id: int,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        project_id = cls._project_id()
        if project_id is None:
            return []

        normalized_limit = max(1, min(int(limit or 10), 50))
        filters = [
            ProjectTask.project_id == project_id,
            ProjectTask.notes.isnot(None),
            ProjectTask.notes.contains(cls.SOURCE_MARKER),
            ProjectTask.notes.contains(f"requester_user_id={int(requester_user_id)}"),
        ]
        if company_id is not None:
            filters.append(ProjectTask.notes.contains(f"requester_company_id={int(company_id)}"))

        tasks = (
            ProjectTask.query.filter(*filters)
            .order_by(ProjectTask.updated_at.desc(), ProjectTask.id.desc())
            .limit(normalized_limit)
            .all()
        )
        return [cls._serialize_task(task) for task in tasks]

    @classmethod
    def create_request(
        cls,
        raw_payload: dict[str, Any],
        *,
        company_id: int,
        company_name: str | None,
        requester_user_id: int,
        requester_name: str | None = None,
    ) -> dict[str, Any]:
        payload = EngineeringSuggestionRequestPayload.model_validate(raw_payload)
        suggestion_type_label = cls.SUGGESTION_TYPE_LABELS.get(payload.suggestion_type, payload.suggestion_type)

        description_lines = [
            "Solicitação estruturada automaticamente via MCP para o Squad de Engenharia.",
            "",
            f"Tipo: {suggestion_type_label}",
            f"Título: {payload.title}",
            f"Escopo: {payload.scope_label}",
            f"Empresa ID: {company_id}",
            f"Empresa: {company_name or '-'}",
            f"Solicitante: {requester_name or f'User {requester_user_id}'}",
            f"Canal de origem: {payload.source_channel}",
            f"Urgência: {payload.urgency}",
            f"Registrado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            "",
            "Objetivo:",
            payload.objective,
        ]
        if payload.evidence_summary:
            description_lines.extend(["", "Contexto / evidências informadas:", payload.evidence_summary])
        if payload.notes:
            description_lines.extend(["", "Observações adicionais:", payload.notes])

        result, error = ProjectTaskService.create_project_task(
            project_code=cls.BACKLOG_PROJECT_CODE,
            task_name=f"{cls.TITLE_PREFIX}{payload.title}",
            user_id=int(requester_user_id),
            allowed_company_ids=None,
            responsible_name=requester_name,
            description="\n".join(description_lines).strip(),
            status="planned",
            stage="inbox",
            priority="high" if payload.urgency in {"high", "critical"} else "normal",
            notes=(
                f"{cls.SOURCE_MARKER}\n"
                f"suggestion_type={payload.suggestion_type}\n"
                f"scope_label={payload.scope_label}\n"
                f"urgency={payload.urgency}\n"
                f"source_origin={payload.source_channel}\n"
                f"requester_company_id={int(company_id)}\n"
                f"requester_user_id={int(requester_user_id)}"
            ),
        )
        if error:
            raise ValueError(error)

        task = (result or {}).get("task")
        if task is None:
            raise ValueError(f"Não foi possível criar o card no backlog {cls.BACKLOG_PROJECT_CODE}.")
        return cls._serialize_task(task)
