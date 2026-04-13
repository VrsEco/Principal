from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from models.project import ProjectTask
from services.project_task_service import ProjectTaskService


class WorkflowRequestPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str = Field(min_length=3, max_length=255)
    business_domain: str = Field(min_length=2, max_length=120)
    objective: str = Field(min_length=10, max_length=3000)
    data_summary: str = Field(min_length=5, max_length=3000)
    source_channel: str = Field(default="ui_workflows_catalog", min_length=2, max_length=64)
    urgency: str = Field(default="medium", pattern="^(low|medium|high|critical)$")
    notes: str | None = Field(default=None, max_length=3000)


class WorkflowBacklogService:
    BACKLOG_PROJECT_CODE = "AA.J.31"
    BACKLOG_STAGE_LABELS = {
        "inbox": "Caixa de Entrada",
        "waiting": "Aguardando",
        "executing": "Executando",
        "pending": "Pendências",
        "suspended": "Suspensos",
        "completed": "Concluídos",
    }

    @classmethod
    def _list_manual_request_tasks(cls) -> list[ProjectTask]:
        project, error = ProjectTaskService.resolve_project_by_code(cls.BACKLOG_PROJECT_CODE, allowed_company_ids=None)
        if error or project is None:
            return []
        return (
            ProjectTask.query.filter(
                ProjectTask.project_id == project.id,
                ProjectTask.notes.isnot(None),
                ProjectTask.notes.contains("source_channel=workflow_request_ui"),
            )
            .order_by(ProjectTask.updated_at.desc(), ProjectTask.id.desc())
            .all()
        )

    @classmethod
    def _serialize_manual_request_task(cls, task: ProjectTask) -> dict[str, Any]:
        stage = str(getattr(task, "stage", None) or "inbox").strip().lower()
        notes = getattr(task, "notes", None) or ""

        def _extract(marker: str) -> str | None:
            prefix = f"{marker}="
            for line in notes.splitlines():
                if line.startswith(prefix):
                    return line[len(prefix):].strip() or None
            return None

        raw_title = str(getattr(task, "what", "") or "").strip()
        title = raw_title.replace("[Novo Workflow] ", "", 1) if raw_title.startswith("[Novo Workflow] ") else raw_title
        return {
            "id": f"manual:{getattr(task, 'id', None)}",
            "title": title,
            "business_domain": _extract("business_domain") or "Novo workflow",
            "status": stage,
            "status_label": cls.BACKLOG_STAGE_LABELS.get(stage, stage or "-"),
            "backlog_task_id": getattr(task, "id", None),
            "backlog_task_code": getattr(task, "code", None),
            "backlog_stage": stage,
            "backlog_stage_label": cls.BACKLOG_STAGE_LABELS.get(stage, stage or "-"),
            "urgency": _extract("urgency") or "medium",
            "created_at": getattr(task, "created_at", None).isoformat() if getattr(task, "created_at", None) else None,
            "updated_at": getattr(task, "updated_at", None).isoformat() if getattr(task, "updated_at", None) else None,
        }

    @classmethod
    def create_request(
        cls,
        raw_payload: dict[str, Any],
        *,
        company_id: int | None,
        requester_user_id: int,
        requester_name: str | None = None,
    ) -> dict[str, Any]:
        payload = WorkflowRequestPayload.model_validate(raw_payload)
        description_lines = [
            "Solicitação estruturada de novo Workflow para catálogo corporativo.",
            "",
            f"Workflow: {payload.title}",
            f"Domínio: {payload.business_domain}",
            f"Solicitante: {requester_name or f'User {requester_user_id}'}",
            f"Company ID: {company_id if company_id is not None else '-'}",
            f"Urgência: {payload.urgency}",
            "",
            "Objetivo de negócio:",
            payload.objective,
            "",
            "Dados / parâmetros / etapas esperadas:",
            payload.data_summary,
        ]
        if payload.notes:
            description_lines.extend(["", "Observações:", payload.notes])

        result, error = ProjectTaskService.create_project_task(
            project_code=cls.BACKLOG_PROJECT_CODE,
            task_name=f"[Novo Workflow] {payload.title}",
            user_id=int(requester_user_id),
            allowed_company_ids=None,
            responsible_name=requester_name,
            description="\n".join(description_lines).strip(),
            status="planned",
            stage="inbox",
            priority="high" if payload.urgency in {"high", "critical"} else "normal",
            notes=(
                "source_channel=workflow_request_ui\n"
                f"business_domain={payload.business_domain}\n"
                f"urgency={payload.urgency}\n"
                f"requester_user_id={requester_user_id}"
            ),
        )
        if error:
            raise ValueError(error)
        task = (result or {}).get("task")
        if task is None:
            raise ValueError("Não foi possível criar o card do workflow no backlog.")
        return cls._serialize_manual_request_task(task)

    @classmethod
    def list_requests(
        cls,
        *,
        active_company: Any | None = None,
        requester_user_id: int,
        requester_name: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        items = [cls._serialize_manual_request_task(task) for task in cls._list_manual_request_tasks()]
        items.sort(key=lambda item: item.get("updated_at") or item.get("created_at") or "", reverse=True)
        return items[:limit]
