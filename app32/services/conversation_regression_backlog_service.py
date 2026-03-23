from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from models import db
from models.project import ProjectTask
from services.project_task_service import ProjectTaskService


def _append_text(base: Optional[str], extra: str) -> str:
    current = str(base or "").strip()
    value = str(extra or "").strip()
    if not value:
        return current
    if not current:
        return value
    if value in current:
        return current
    return f"{current}\n\n{value}"


class ConversationRegressionBacklogService:
    """Sincroniza regressões conversacionais com o backlog AA.J.31."""

    DEFAULT_PROJECT_CODE = "AA.J.31"

    @staticmethod
    def find_existing_task_by_code(task_code: Optional[str]) -> Optional[ProjectTask]:
        normalized = str(task_code or "").strip()
        if not normalized:
            return None
        task_id = ProjectTaskService.extract_id_from_code(normalized)
        if not task_id:
            return None
        return ProjectTask.query.get(task_id)

    @staticmethod
    def build_task_name(item: Dict[str, Any]) -> str:
        summary = str(item.get("summary") or "").strip()
        case_id = str(item.get("case_id") or "").strip()
        chapter = str(item.get("chapter") or "").strip()
        if summary:
            return summary[:200]
        return f"[QA_CONVERSA][{chapter}] {case_id}"[:200]

    @staticmethod
    def build_task_description(item: Dict[str, Any]) -> str:
        return "\n".join(
            [
                "Origem: suíte de regressão conversacional V6.",
                f"Caso: {item.get('case_id')}",
                f"Capítulo: {item.get('chapter')}",
                f"Classe de falha: {item.get('failure_class')}",
                f"Workflow Gap ID: {item.get('workflow_gap_id') or 'N/A'}",
                f"Resumo: {item.get('summary') or 'N/A'}",
            ]
        )

    @staticmethod
    def build_task_notes(item: Dict[str, Any]) -> str:
        return "\n".join(
            [
                "Card sincronizado automaticamente pela suíte conversation_regression_v6.",
                f"case_id={item.get('case_id')}",
                f"chapter={item.get('chapter')}",
                f"failure_class={item.get('failure_class')}",
                f"workflow_gap_id={item.get('workflow_gap_id') or 'N/A'}",
                f"app_task_code_origem={item.get('app_task_code') or 'N/A'}",
            ]
        )

    @staticmethod
    def build_log_entry(item: Dict[str, Any], action: str) -> Dict[str, Any]:
        return {
            "date": datetime.utcnow().isoformat(),
            "author": "conversation_regression_v6",
            "type": "conversation_regression_sync",
            "action": action,
            "case_id": item.get("case_id"),
            "chapter": item.get("chapter"),
            "failure_class": item.get("failure_class"),
            "workflow_gap_id": item.get("workflow_gap_id"),
        }

    @staticmethod
    def update_existing_task(task: ProjectTask, item: Dict[str, Any]) -> ProjectTask:
        task.status = str(item.get("status") or task.status or "planned").strip() or "planned"
        task.stage = str(item.get("stage") or task.stage or "inbox").strip() or "inbox"
        if task.stage == "completed" and getattr(task, "completion_date", None) is None:
            task.completion_date = datetime.utcnow().date()
        task.notes = _append_text(task.notes, ConversationRegressionBacklogService.build_task_notes(item))
        logs = list(task.logs or [])
        logs.append(ConversationRegressionBacklogService.build_log_entry(item, "updated"))
        task.logs = logs
        return task

    @staticmethod
    def create_new_task(
        item: Dict[str, Any],
        *,
        project_code: str,
        user_id: int,
    ) -> Tuple[Optional[ProjectTask], Optional[str]]:
        result, error = ProjectTaskService.create_project_task(
            project_code=project_code,
            task_name=ConversationRegressionBacklogService.build_task_name(item),
            user_id=user_id,
            responsible_name=None,
            due_date=None,
            description=ConversationRegressionBacklogService.build_task_description(item),
            amount=None,
            status=str(item.get("status") or "planned"),
            stage=str(item.get("stage") or "inbox"),
            priority="normal",
            notes=ConversationRegressionBacklogService.build_task_notes(item),
            allowed_company_ids=None,
        )
        if error:
            return None, error
        task = (result or {}).get("task") if isinstance(result, dict) else None
        if task is None:
            return None, "Resultado sem task ao criar backlog de regressão conversacional."
        if str(item.get("stage") or "").strip() == "completed" and getattr(task, "completion_date", None) is None:
            task.completion_date = datetime.utcnow().date()
        logs = list(task.logs or [])
        logs.append(ConversationRegressionBacklogService.build_log_entry(item, "created"))
        task.logs = logs
        return task, None

    @staticmethod
    def sync_item(
        item: Dict[str, Any],
        *,
        project_code: str,
        user_id: int,
        persist: bool = True,
    ) -> Dict[str, Any]:
        existing = ConversationRegressionBacklogService.find_existing_task_by_code(item.get("app_task_code"))
        if existing is not None:
            task = ConversationRegressionBacklogService.update_existing_task(existing, item)
            if persist:
                db.session.commit()
            return {"action": "updated", "task_id": task.id, "task_code": task.code}

        task, error = ConversationRegressionBacklogService.create_new_task(
            item,
            project_code=project_code,
            user_id=user_id,
        )
        if error:
            if persist:
                db.session.rollback()
            return {"action": "error", "error": error, "case_id": item.get("case_id")}
        if persist:
            db.session.commit()
        return {"action": "created", "task_id": task.id, "task_code": task.code}

    @staticmethod
    def apply_sync_payload(
        payload: Dict[str, Any],
        *,
        user_id: int,
        persist: bool = True,
    ) -> Dict[str, Any]:
        project_code = str(payload.get("project_code") or ConversationRegressionBacklogService.DEFAULT_PROJECT_CODE).strip()
        items = list(payload.get("items") or [])
        results: List[Dict[str, Any]] = []
        for item in items:
            results.append(
                ConversationRegressionBacklogService.sync_item(
                    dict(item),
                    project_code=project_code,
                    user_id=user_id,
                    persist=persist,
                )
            )
        return {
            "project_code": project_code,
            "integration": payload.get("integration") or "conversation_regression_v6",
            "processed": len(items),
            "results": results,
        }
