from __future__ import annotations

import logging
import re
import unicodedata
from typing import Any

from models.project import ProjectTask
from services.project_task_service import ProjectTaskService
from services.tool_first_catalog_service import ToolFirstCatalogService

logger = logging.getLogger(__name__)


class ToolBacklogService:
    BACKLOG_PROJECT_CODE = "AA.J.31"
    BACKLOG_STAGE_LABELS = {
        "inbox": "Caixa de Entrada",
        "waiting": "Aguardando",
        "executing": "Executando",
        "pending": "Pendências",
        "suspended": "Suspensos",
        "completed": "Concluídos",
    }

    @staticmethod
    def _slugify(value: str) -> str:
        text = unicodedata.normalize("NFKD", str(value or "").strip().lower())
        text = "".join(ch for ch in text if not unicodedata.combining(ch))
        text = re.sub(r"[^a-z0-9]+", "-", text)
        return re.sub(r"-{2,}", "-", text).strip("-") or "nova-tool"

    @classmethod
    def _find_backlog_task(cls, domain_key: str, tool_name: str) -> ProjectTask | None:
        project, error = ProjectTaskService.resolve_project_by_code(cls.BACKLOG_PROJECT_CODE, allowed_company_ids=None)
        if error or project is None:
            return None

        marker = f"tool_catalog_key={domain_key}:{tool_name}"
        return (
            ProjectTask.query.filter(
                ProjectTask.project_id == project.id,
                ProjectTask.notes.isnot(None),
                ProjectTask.notes.contains(marker),
            )
            .order_by(ProjectTask.id.asc())
            .first()
        )

    @classmethod
    def _build_task_description(cls, domain: dict[str, Any], tool: dict[str, Any]) -> str:
        lines = [
            "Tool planejada do catálogo operacional sincronizada com o backlog AA.J.31.",
            "",
            f"Domínio: {domain.get('title')}",
            f"Chave do domínio: {domain.get('key')}",
            f"Surface: {domain.get('surface')}",
            f"Status do domínio: {domain.get('status')}",
            f"Tool: {tool.get('name')}",
            "",
            "Descrição do domínio:",
            domain.get("description") or "Sem descrição.",
        ]
        governance = domain.get("governance") or []
        if governance:
            lines.extend(["", "Governança:"] + [f"- {rule}" for rule in governance[:5]])
        return "\n".join(lines).strip()

    @classmethod
    def _serialize_item(cls, domain: dict[str, Any], tool: dict[str, Any], task: ProjectTask) -> dict[str, Any]:
        stage = str(getattr(task, "stage", None) or "pending").strip().lower()
        return {
            "id": f"tool:{domain.get('key')}:{tool.get('name')}",
            "title": tool.get("name"),
            "slug": cls._slugify(tool.get("name") or ""),
            "domain_key": domain.get("key"),
            "domain_title": domain.get("title"),
            "surface": domain.get("surface"),
            "status": stage,
            "status_label": cls.BACKLOG_STAGE_LABELS.get(stage, stage or "-"),
            "risk": tool.get("risk") or "planned",
            "backlog_task_id": getattr(task, "id", None),
            "backlog_task_code": getattr(task, "code", None),
            "backlog_stage": stage,
            "backlog_stage_label": cls.BACKLOG_STAGE_LABELS.get(stage, stage or "-"),
            "created_at": getattr(task, "created_at", None).isoformat() if getattr(task, "created_at", None) else None,
            "updated_at": getattr(task, "updated_at", None).isoformat() if getattr(task, "updated_at", None) else None,
        }

    @classmethod
    def ensure_catalog_backlog_tasks(
        cls,
        *,
        active_company: Any | None = None,
        requester_user_id: int,
        requester_name: str | None = None,
    ) -> list[dict[str, Any]]:
        catalog = ToolFirstCatalogService.build_catalog(active_company)
        items: list[dict[str, Any]] = []

        for domain in catalog.get("domains") or []:
            for tool in domain.get("planned_tools") or []:
                tool_name = str(tool.get("name") or "").strip()
                if not tool_name:
                    continue

                task = cls._find_backlog_task(str(domain.get("key") or ""), tool_name)
                if task is None:
                    result, error = ProjectTaskService.create_project_task(
                        project_code=cls.BACKLOG_PROJECT_CODE,
                        task_name=f"[Tool Catálogo] {tool_name} - {domain.get('title')}",
                        user_id=int(requester_user_id),
                        allowed_company_ids=None,
                        responsible_name=requester_name,
                        description=cls._build_task_description(domain, tool),
                        status="planned",
                        stage="pending",
                        priority="normal",
                        notes=(
                            f"tool_catalog_key={domain.get('key')}:{tool_name}\n"
                            "source_channel=tool_catalog\n"
                            f"domain_key={domain.get('key')}\n"
                            f"surface={domain.get('surface')}\n"
                            f"domain_status={domain.get('status')}"
                        ),
                    )
                    if error:
                        logger.warning(
                            "Falha ao sincronizar backlog da tool %s/%s: %s",
                            domain.get("key"),
                            tool_name,
                            error,
                        )
                        continue
                    task = (result or {}).get("task")

                if task is not None:
                    items.append(cls._serialize_item(domain, tool, task))

        items.sort(key=lambda item: item.get("updated_at") or item.get("created_at") or "", reverse=True)
        return items

    @classmethod
    def list_requests(
        cls,
        *,
        active_company: Any | None = None,
        requester_user_id: int,
        requester_name: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        items = cls.ensure_catalog_backlog_tasks(
            active_company=active_company,
            requester_user_id=requester_user_id,
            requester_name=requester_name,
        )
        return items[:limit]
