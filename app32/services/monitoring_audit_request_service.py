
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from models.project import ProjectTask
from services.project_task_service import ProjectTaskService


class MonitoringAuditRequestPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str = Field(min_length=3, max_length=255)
    request_kind: str = Field(default="verification", pattern="^(verification|audit)$")
    scope_label: str = Field(min_length=3, max_length=120)
    objective: str = Field(min_length=10, max_length=3000)
    source_filter: str | None = Field(default=None, pattern="^(human_review|sapiens_workflow|agent_action)?$")
    urgency: str = Field(default="medium", pattern="^(low|medium|high|critical)$")
    notes: str | None = Field(default=None, max_length=3000)
    evidence_summary: str | None = Field(default=None, max_length=3000)


class MonitoringAuditRequestService:
    BACKLOG_PROJECT_CODE = "AA.J.31"
    SOURCE_MARKER = "source_channel=ai_monitoring_request_ui"
    BACKLOG_STAGE_LABELS = {
        "inbox": "Caixa de Entrada",
        "waiting": "Aguardando",
        "executing": "Executando",
        "pending": "Pendências",
        "suspended": "Suspensos",
        "completed": "Concluídos",
    }
    REQUEST_KIND_LABELS = {
        "verification": "Verificação",
        "audit": "Auditoria",
    }
    SOURCE_LABELS = {
        "human_review": "Revisões humanas",
        "sapiens_workflow": "Sapiens / workflows",
        "agent_action": "Ações de agentes / MCP",
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
    def _serialize_task(cls, task: ProjectTask) -> dict[str, Any]:
        stage = str(getattr(task, "stage", None) or "inbox").strip().lower()
        notes = getattr(task, "notes", None) or ""

        def _extract(marker: str) -> str | None:
            prefix = f"{marker}="
            for line in notes.splitlines():
                if line.startswith(prefix):
                    return line[len(prefix):].strip() or None
            return None

        raw_title = str(getattr(task, "what", "") or "").strip()
        title = raw_title.replace("[Monitoramento IA] ", "", 1) if raw_title.startswith("[Monitoramento IA] ") else raw_title
        request_kind = _extract("request_kind") or "verification"
        source_filter = _extract("source_filter") or None
        return {
            "id": getattr(task, "id", None),
            "title": title,
            "request_kind": request_kind,
            "request_kind_label": cls.REQUEST_KIND_LABELS.get(request_kind, request_kind),
            "scope_label": _extract("scope_label") or "Monitoramento e Auditoria",
            "source_filter": source_filter,
            "source_filter_label": cls.SOURCE_LABELS.get(source_filter or "", "Todas as fontes"),
            "urgency": _extract("urgency") or "medium",
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
            filters.append(ProjectTask.notes.contains(f"company_id={int(company_id)}"))

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
        payload = MonitoringAuditRequestPayload.model_validate(raw_payload)

        request_kind_label = cls.REQUEST_KIND_LABELS.get(payload.request_kind, payload.request_kind)
        source_label = cls.SOURCE_LABELS.get(payload.source_filter or "", "Todas as fontes")
        description_lines = [
            "Solicitação estruturada pela tela de Monitoramento e Auditoria da IA Corporativa.",
            "",
            f"Tipo: {request_kind_label}",
            f"Título: {payload.title}",
            f"Escopo: {payload.scope_label}",
            f"Empresa ID: {company_id}",
            f"Empresa: {company_name or '-'}",
            f"Solicitante: {requester_name or f'User {requester_user_id}'}",
            f"Urgência: {payload.urgency}",
            f"Fonte priorizada: {source_label}",
            f"Registrado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            "",
            "Objetivo:",
            payload.objective,
        ]
        if payload.evidence_summary:
            description_lines.extend(["", "Contexto / evidências capturadas na tela:", payload.evidence_summary])
        if payload.notes:
            description_lines.extend(["", "Observações adicionais:", payload.notes])

        result, error = ProjectTaskService.create_project_task(
            project_code=cls.BACKLOG_PROJECT_CODE,
            task_name=f"[Monitoramento IA] {payload.title}",
            user_id=int(requester_user_id),
            allowed_company_ids=None,
            responsible_name=requester_name,
            description="\n".join(description_lines).strip(),
            status="planned",
            stage="inbox",
            priority="high" if payload.urgency in {"high", "critical"} else "normal",
            notes=(
                f"{cls.SOURCE_MARKER}\n"
                f"request_kind={payload.request_kind}\n"
                f"scope_label={payload.scope_label}\n"
                f"source_filter={payload.source_filter or ''}\n"
                f"urgency={payload.urgency}\n"
                f"company_id={int(company_id)}\n"
                f"requester_user_id={int(requester_user_id)}"
            ),
        )
        if error:
            raise ValueError(error)

        task = (result or {}).get("task")
        if task is None:
            raise ValueError("Não foi possível criar o card no backlog AA.J.31.")
        return cls._serialize_task(task)
