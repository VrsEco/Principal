from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from models.project import ProjectTask
from services.project_task_service import ProjectTaskService


class AICapabilityRequestPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str = Field(min_length=3, max_length=255)
    capability_key: str | None = Field(default=None, max_length=255)
    capability_name: str | None = Field(default=None, max_length=255)
    business_domain: str = Field(min_length=2, max_length=120)
    issue_type: str = Field(default="bug", pattern="^(bug|improvement|access|rollout|configuration|audit)$")
    urgency: str = Field(default="medium", pattern="^(low|medium|high|critical)$")
    objective: str = Field(min_length=10, max_length=3000)
    data_summary: str | None = Field(default=None, max_length=3000)
    notes: str | None = Field(default=None, max_length=3000)
    source_channel: str = Field(default="ui_ai_capabilities", min_length=2, max_length=64)


class AICapabilityBacklogService:
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
                ProjectTask.notes.contains("source_channel=ai_capabilities_request_ui"),
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
        title = raw_title.replace("[Capability IA] ", "", 1) if raw_title.startswith("[Capability IA] ") else raw_title
        return {
            "id": f"manual:{getattr(task, 'id', None)}",
            "title": title,
            "business_domain": _extract("business_domain") or "IA Corporativa",
            "capability_key": _extract("capability_key"),
            "capability_name": _extract("capability_name"),
            "issue_type": _extract("issue_type") or "bug",
            "source_kind": "manual_request",
            "status": stage,
            "status_label": cls.BACKLOG_STAGE_LABELS.get(stage, stage or "-"),
            "backlog_task_id": getattr(task, "id", None),
            "backlog_task_code": getattr(task, "code", None),
            "backlog_task_href": f"/my-work/project-task/{getattr(task, 'id', None)}" if getattr(task, "id", None) else None,
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
        payload = AICapabilityRequestPayload.model_validate(raw_payload)
        description_lines = [
            "Solicitação operacional aberta a partir da Central de Capacidades de IA.",
            "",
            f"Título: {payload.title}",
            f"Capability: {payload.capability_name or payload.capability_key or '-'}",
            f"Chave técnica: {payload.capability_key or '-'}",
            f"Domínio: {payload.business_domain}",
            f"Tipo de item: {payload.issue_type}",
            f"Solicitante: {requester_name or f'User {requester_user_id}'}",
            f"Company ID: {company_id if company_id is not None else '-'}",
            f"Urgência: {payload.urgency}",
            "",
            "Problema / objetivo:",
            payload.objective,
        ]
        if payload.data_summary:
            description_lines.extend(["", "Contexto / evidências / dados:", payload.data_summary])
        if payload.notes:
            description_lines.extend(["", "Observações adicionais:", payload.notes])

        result, error = ProjectTaskService.create_project_task(
            project_code=cls.BACKLOG_PROJECT_CODE,
            task_name=f"[Capability IA] {payload.title}",
            user_id=int(requester_user_id),
            allowed_company_ids=None,
            responsible_name=requester_name,
            description="\n".join(description_lines).strip(),
            status="planned",
            stage="inbox",
            priority="high" if payload.urgency in {"high", "critical"} else "normal",
            notes=(
                "source_channel=ai_capabilities_request_ui\n"
                f"business_domain={payload.business_domain}\n"
                f"capability_key={payload.capability_key or ''}\n"
                f"capability_name={payload.capability_name or ''}\n"
                f"issue_type={payload.issue_type}\n"
                f"urgency={payload.urgency}\n"
                f"requester_user_id={requester_user_id}"
            ),
        )
        if error:
            raise ValueError(error)
        task = (result or {}).get("task")
        if task is None:
            raise ValueError("Não foi possível criar o card da capability no backlog.")
        return cls._serialize_manual_request_task(task)

    @classmethod
    def list_requests(
        cls,
        *,
        capability_key: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        items = [cls._serialize_manual_request_task(task) for task in cls._list_manual_request_tasks()]
        if capability_key:
            capability_key_normalized = capability_key.strip()
            items = [item for item in items if (item.get("capability_key") or "").strip() == capability_key_normalized]
        items.sort(key=lambda item: item.get("updated_at") or item.get("created_at") or "", reverse=True)
        return items[:limit]
