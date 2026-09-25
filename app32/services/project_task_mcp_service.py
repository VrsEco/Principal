from __future__ import annotations

import os
from collections import Counter
from datetime import datetime
from typing import Any

from sqlalchemy import func

from models import db
from models.project import Project, ProjectTask
from services.project_task_service import ProjectTaskService


def _coerce_positive_int(value: Any, default: int, *, ceiling: int | None = None) -> int:
    try:
        parsed = int(str(value).strip())
    except Exception:
        parsed = default
    if parsed <= 0:
        parsed = default
    if ceiling is not None:
        parsed = min(parsed, ceiling)
    return parsed


class ProjectTaskMCPService:
    UPDATE_ALLOWED_FIELDS = frozenset(
        {
            "task_name",
            "responsible_name",
            "due_date",
            "description",
            "priority",
            "notes",
            "status",
            "stage",
        }
    )

    @staticmethod
    def _serialize_task(task: ProjectTask) -> dict[str, Any]:
        payload = task.to_dict()
        payload["is_deleted"] = bool(getattr(task, "is_deleted", False))
        payload["deleted_at"] = (
            task.deleted_at.isoformat() if getattr(task, "deleted_at", None) else None
        )
        payload["deleted_by_user_id"] = getattr(task, "deleted_by_user_id", None)
        payload["delete_reason"] = getattr(task, "delete_reason", None)
        payload["company_id"] = getattr(task.project, "company_id", None) if getattr(task, "project", None) else None
        return payload

    @staticmethod
    def _base_query(*, company_id: int, include_deleted: bool = False):
        query = (
            ProjectTask.query.join(Project, Project.id == ProjectTask.project_id)
            .filter(Project.company_id == int(company_id))
        )
        if not include_deleted:
            query = query.filter(ProjectTask.is_deleted.is_(False), Project.is_deleted.is_(False))
        return query

    @staticmethod
    def get_task(*, company_id: int, task_id: int, include_deleted: bool = False) -> tuple[ProjectTask | None, str | None]:
        task = (
            ProjectTaskMCPService._base_query(company_id=company_id, include_deleted=include_deleted)
            .filter(ProjectTask.id == int(task_id))
            .first()
        )
        if task is None:
            return None, "Atividade de projeto não encontrada no tenant informado."
        return task, None

    @staticmethod
    def list_tasks(
        *,
        company_id: int,
        project_id: int | None = None,
        include_deleted: bool = False,
        limit: int = 50,
        mine_only: bool = False,
        open_only: bool = False,
        actor_user_id: int | None = None,
    ) -> tuple[dict[str, Any], str | None]:
        safe_limit = _coerce_positive_int(
            limit,
            50,
            ceiling=_coerce_positive_int(os.environ.get("APP32_MCP_MAX_LIST_LIMIT"), 200),
        )
        query = ProjectTaskMCPService._base_query(
            company_id=company_id,
            include_deleted=include_deleted,
        )
        if project_id:
            query = query.filter(ProjectTask.project_id == int(project_id))

        employee_id = None
        if mine_only:
            from models.employee import Employee

            if not actor_user_id:
                return {}, "Usuário autenticado obrigatório para consultar minhas atividades."
            employee = Employee.query.filter(
                Employee.user_id == int(actor_user_id),
                Employee.company_id == int(company_id),
                Employee.status.in_(("active", "vacation")),
            ).one_or_none()
            if employee is None:
                return {}, "Colaborador ativo não encontrado para o usuário nesta empresa."
            employee_id = int(employee.id)
            # Nunca inferir autoria pelo texto legado `who` ou pelo nome.
            query = query.filter(ProjectTask.employee_id == employee_id)
        if open_only:
            query = query.filter(
                func.coalesce(ProjectTask.status, "planned").notin_(("completed", "cancelled")),
                func.coalesce(ProjectTask.stage, "inbox").notin_(("completed", "cancelled")),
                ProjectTask.completion_date.is_(None),
            )

        tasks = query.order_by(ProjectTask.updated_at.desc(), ProjectTask.id.desc()).limit(safe_limit).all()
        return {
            "items": [ProjectTaskMCPService._serialize_task(task) for task in tasks],
            "count": len(tasks),
            "limit": safe_limit,
            "company_id": int(company_id),
            "project_id": int(project_id) if project_id else None,
            "include_deleted": bool(include_deleted),
            "mine_only": bool(mine_only),
            "open_only": bool(open_only),
            "employee_id": employee_id,
        }, None

    @staticmethod
    def build_analytics_report(
        *,
        company_id: int,
        project_id: int | None = None,
        include_deleted: bool = True,
        limit: int = 200,
    ) -> tuple[dict[str, Any], str | None]:
        listing, error = ProjectTaskMCPService.list_tasks(
            company_id=company_id,
            project_id=project_id,
            include_deleted=include_deleted,
            limit=limit,
        )
        if error:
            return {}, error

        items = list(listing.get("items") or [])
        by_stage = Counter(str(item.get("stage") or "unknown") for item in items)
        by_status = Counter(str(item.get("status") or "unknown") for item in items)
        by_priority = Counter(str(item.get("priority") or "normal") for item in items)

        return {
            "summary": {
                "company_id": int(company_id),
                "project_id": int(project_id) if project_id else None,
                "count": len(items),
                "include_deleted": bool(include_deleted),
            },
            "metrics": {
                "by_stage": dict(by_stage),
                "by_status": dict(by_status),
                "by_priority": dict(by_priority),
                "deleted_count": sum(1 for item in items if item.get("is_deleted")),
            },
            "items": items,
        }, None

    @staticmethod
    def create_task(
        *,
        company_id: int,
        user_id: int,
        project_code: str,
        task_name: str,
        responsible_name: str | None = None,
        due_date: str | None = None,
        description: str | None = None,
        priority: str = "normal",
        notes: str | None = None,
    ) -> tuple[dict[str, Any] | None, str | None]:
        result, error = ProjectTaskService.create_project_task(
            project_code=project_code,
            task_name=task_name,
            user_id=user_id,
            allowed_company_ids=[int(company_id)],
            responsible_name=responsible_name,
            due_date=due_date,
            description=description,
            priority=priority,
            notes=notes,
        )
        if error:
            return None, error
        if not result:
            return None, "Falha ao criar atividade de projeto."

        task = result["task"]
        return {
            "task": ProjectTaskMCPService._serialize_task(task),
            "project_code": getattr(result["project"], "code", project_code),
            "project_name": getattr(result["project"], "name", None),
        }, None

    @staticmethod
    def update_task(
        *,
        company_id: int,
        task_id: int,
        changes: dict[str, Any],
    ) -> tuple[dict[str, Any] | None, str | None]:
        if not isinstance(changes, dict) or not changes:
            return None, "Atualização exige um objeto não vazio."
        normalized_changes = dict(changes)
        invalid_fields = sorted(set(normalized_changes) - ProjectTaskMCPService.UPDATE_ALLOWED_FIELDS)
        if invalid_fields:
            return None, f"Campos não permitidos na atualização MCP: {', '.join(invalid_fields)}"

        max_fields = _coerce_positive_int(os.environ.get("APP32_MCP_MAX_UPDATE_FIELDS"), 6)
        if len(normalized_changes) > max_fields:
            return None, f"Atualização excede o limite seguro de {max_fields} campos por operação."

        for field, allowed in {
            "status": {"planned", "in_progress", "completed", "cancelled"},
            "stage": {"inbox", "waiting", "executing", "pending", "suspended", "completed"},
            "priority": {"low", "normal", "high", "urgent"},
        }.items():
            if field in normalized_changes:
                value = normalized_changes[field]
                if not isinstance(value, str) or value.strip() not in allowed:
                    return None, f"Valor inválido para {field}."
                normalized_changes[field] = value.strip()
        if "task_name" in normalized_changes:
            value = normalized_changes["task_name"]
            if not isinstance(value, str) or not value.strip():
                return None, "Nome da atividade não pode ser vazio."
        if "status" in normalized_changes and "stage" in normalized_changes:
            if (normalized_changes["status"] == "completed") != (normalized_changes["stage"] == "completed"):
                return None, "Status e etapa de conclusão incompatíveis."
        # Validate dates before touching the ORM object: a rejected payload must
        # not leave dirty attributes that a later operation could commit.
        if "due_date" in normalized_changes:
            parsed_due_date, due_date_error = ProjectTaskService.parse_due_date(normalized_changes["due_date"])
            if due_date_error:
                return None, due_date_error

        task, error = ProjectTaskMCPService.get_task(company_id=company_id, task_id=task_id)
        if error:
            return None, error
        if task is None:
            return None, "Atividade não encontrada."

        if task.is_deleted:
            return None, "Não é permitido alterar atividade já soft-deletada."

        if "task_name" in normalized_changes:
            task.what = str(normalized_changes["task_name"]).strip()
        if "responsible_name" in normalized_changes:
            task.who = str(normalized_changes["responsible_name"]).strip() or None
        if "due_date" in normalized_changes:
            task.due_date = parsed_due_date
        if "description" in normalized_changes:
            task.how = str(normalized_changes["description"]).strip() or None
        if "priority" in normalized_changes:
            task.priority = str(normalized_changes["priority"]).strip() or "normal"
        if "notes" in normalized_changes:
            task.notes = str(normalized_changes["notes"]).strip() or None
        if "status" in normalized_changes:
            task.status = str(normalized_changes["status"]).strip() or task.status
        if "stage" in normalized_changes:
            task.stage = str(normalized_changes["stage"]).strip() or task.stage

        if normalized_changes.get("status") == "completed":
            task.stage = "completed"
        elif "status" in normalized_changes and task.stage == "completed":
            task.stage = "executing" if task.status == "in_progress" else "inbox"
        elif "stage" in normalized_changes and task.stage != "completed" and task.status == "completed":
            task.status = "in_progress" if task.stage == "executing" else "planned"
        if task.stage == "completed":
            task.status = "completed"
            if task.completion_date is None:
                task.completion_date = datetime.utcnow().date()
        elif "stage" in normalized_changes or "status" in normalized_changes:
            task.completion_date = None

        if task.project:
            task.project.update_progress()

        db.session.commit()
        return {"task": ProjectTaskMCPService._serialize_task(task)}, None

    @staticmethod
    def soft_delete_task(
        *,
        company_id: int,
        task_id: int,
        user_id: int,
        reason: str,
    ) -> tuple[dict[str, Any] | None, str | None]:
        task, error = ProjectTaskMCPService.get_task(
            company_id=company_id,
            task_id=task_id,
            include_deleted=True,
        )
        if error:
            return None, error
        if task is None:
            return None, "Atividade não encontrada."
        if task.is_deleted:
            return None, "Atividade já está removida logicamente."

        task.is_deleted = True
        task.deleted_at = datetime.utcnow()
        task.deleted_by_user_id = int(user_id)
        task.delete_reason = str(reason or "").strip() or "soft delete via MCP"
        if task.project:
            task.project.update_progress()
        db.session.commit()
        return {"task": ProjectTaskMCPService._serialize_task(task)}, None

    @staticmethod
    def restore_task(
        *,
        company_id: int,
        task_id: int,
    ) -> tuple[dict[str, Any] | None, str | None]:
        task, error = ProjectTaskMCPService.get_task(
            company_id=company_id,
            task_id=task_id,
            include_deleted=True,
        )
        if error:
            return None, error
        if task is None:
            return None, "Atividade não encontrada."
        if not task.is_deleted:
            return None, "Atividade não está soft-deletada."

        task.is_deleted = False
        task.deleted_at = None
        task.deleted_by_user_id = None
        task.delete_reason = None
        if task.project:
            task.project.update_progress()
        db.session.commit()
        return {"task": ProjectTaskMCPService._serialize_task(task)}, None

