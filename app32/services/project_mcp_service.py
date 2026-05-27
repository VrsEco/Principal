from __future__ import annotations

import os
from datetime import datetime
from typing import Any

from models import db
from models.company import Company
from models import OKRArea, OKRGlobal
from models.project import Project
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


class ProjectMCPService:
    UPDATE_ALLOWED_FIELDS = frozenset(
        {
            "name",
            "description",
            "responsible",
            "responsible_name",
            "owner",
            "status",
            "start_date",
            "due_date",
            "end_date",
            "deadline",
            "notes",
            "priority",
            "okr_links",
        }
    )

    @staticmethod
    def _normalize_okr_links(value: Any, *, company_id: int) -> list[int] | None:
        if value in (None, ""):
            return None
        if not isinstance(value, (list, tuple, set)):
            raise ValueError("okr_links deve ser uma lista de IDs de OKR.")

        normalized: list[int] = []
        for item in value:
            try:
                normalized.append(int(item))
            except Exception as exc:
                raise ValueError("okr_links deve conter apenas inteiros.") from exc

        if not normalized:
            return []

        global_ids = {
            row[0]
            for row in (
                OKRGlobal.query.filter(
                    OKRGlobal.company_id == int(company_id),
                    OKRGlobal.id.in_(normalized),
                )
                .with_entities(OKRGlobal.id)
                .all()
            )
        }
        area_ids = {
            row[0]
            for row in (
                OKRArea.query.filter(
                    OKRArea.company_id == int(company_id),
                    OKRArea.id.in_(normalized),
                )
                .with_entities(OKRArea.id)
                .all()
            )
        }
        allowed_ids = global_ids | area_ids
        missing = [okr_id for okr_id in normalized if okr_id not in allowed_ids]
        if missing:
            raise ValueError(
                "Os seguintes IDs em okr_links não pertencem à empresa informada ou não existem: "
                + ", ".join(str(item) for item in missing)
            )
        return normalized

    @staticmethod
    def _serialize_project(project: Project) -> dict[str, Any]:
        payload = project.to_dict()
        payload["responsible_name"] = getattr(project, "owner", None)
        payload["due_date"] = payload.get("end_date") or payload.get("deadline")
        return payload

    @staticmethod
    def _base_query(*, company_id: int, include_deleted: bool = False):
        query = Project.query.filter(Project.company_id == int(company_id))
        if not include_deleted:
            query = query.filter(Project.is_deleted.is_(False))
        return query

    @staticmethod
    def get_project(
        *,
        company_id: int,
        project_id: int | None = None,
        project_code: str | None = None,
        include_deleted: bool = False,
    ) -> tuple[Project | None, str | None]:
        query = ProjectMCPService._base_query(company_id=company_id, include_deleted=include_deleted)
        project = None

        if project_id:
            project = query.filter(Project.id == int(project_id)).first()
        elif project_code:
            company_prefix, code_sequence = ProjectTaskService.parse_project_code(project_code)
            if not company_prefix or not code_sequence:
                return None, "project_code inválido. Use o padrão EMPRESA.J.ID."
            company = Company.query.get(int(company_id))
            expected_prefix = ProjectTaskService._sanitize_company_code(
                getattr(company, "client_code", None) or getattr(company, "name", None),
                int(company_id),
            )
            if company_prefix != expected_prefix:
                return None, "project_code não pertence ao tenant informado."
            project = query.filter(Project.code_sequence == int(code_sequence)).first()
        else:
            return None, "Informe project_id ou project_code."

        if project is None:
            return None, "Projeto não encontrado no tenant informado."
        return project, None

    @staticmethod
    def create_project(
        *,
        company_id: int,
        name: str,
        description: str | None = None,
        responsible_name: str | None = None,
        start_date: str | None = None,
        due_date: str | None = None,
        okr_links: list[int] | None = None,
    ) -> tuple[dict[str, Any] | None, str | None]:
        normalized_name = str(name or "").strip()
        if not normalized_name:
            return None, "Informe o nome do projeto."

        company = Company.query.get(int(company_id))
        if company is None:
            return None, "Empresa não encontrada."

        parsed_start_date, start_date_error = ProjectTaskService.parse_due_date(start_date)
        if start_date_error:
            return None, start_date_error
        parsed_due_date, due_date_error = ProjectTaskService.parse_due_date(due_date)
        if due_date_error:
            return None, due_date_error
        if parsed_start_date and parsed_due_date and parsed_due_date < parsed_start_date:
            return None, "due_date não pode ser menor que start_date."

        try:
            normalized_okr_links = ProjectMCPService._normalize_okr_links(
                okr_links,
                company_id=int(company_id),
            )
        except ValueError as exc:
            return None, str(exc)

        project = Project(
            company_id=int(company_id),
            name=normalized_name,
            description=(str(description).strip() or None) if description else None,
            owner=(str(responsible_name).strip() or None) if responsible_name else None,
            start_date=parsed_start_date,
            end_date=parsed_due_date,
            status="planned",
            okr_links=normalized_okr_links,
        )
        db.session.add(project)
        db.session.commit()
        return {"project": ProjectMCPService._serialize_project(project)}, None

    @staticmethod
    def list_projects(
        *,
        company_id: int,
        status: str | None = None,
        include_deleted: bool = False,
        limit: int = 50,
    ) -> tuple[dict[str, Any], str | None]:
        safe_limit = _coerce_positive_int(
            limit,
            50,
            ceiling=_coerce_positive_int(os.environ.get("APP32_MCP_MAX_LIST_LIMIT"), 200),
        )
        query = ProjectMCPService._base_query(company_id=company_id, include_deleted=include_deleted)
        if str(status or "").strip():
            query = query.filter(Project.status == str(status).strip())

        projects = query.order_by(Project.updated_at.desc(), Project.id.desc()).limit(safe_limit).all()
        return {
            "items": [ProjectMCPService._serialize_project(project) for project in projects],
            "count": len(projects),
            "limit": safe_limit,
            "company_id": int(company_id),
            "status": str(status).strip() or None,
            "include_deleted": bool(include_deleted),
        }, None

    @staticmethod
    def update_project(
        *,
        company_id: int,
        project_id: int | None = None,
        project_code: str | None = None,
        changes: dict[str, Any],
    ) -> tuple[dict[str, Any] | None, str | None]:
        normalized_changes = dict(changes or {})
        invalid_fields = sorted(set(normalized_changes) - ProjectMCPService.UPDATE_ALLOWED_FIELDS)
        if invalid_fields:
            return None, f"Campos não permitidos na atualização MCP: {', '.join(invalid_fields)}"

        max_fields = _coerce_positive_int(os.environ.get("APP32_MCP_MAX_UPDATE_FIELDS"), 6)
        if len(normalized_changes) > max_fields:
            return None, f"Atualização excede o limite seguro de {max_fields} campos por operação."

        project, error = ProjectMCPService.get_project(
            company_id=company_id,
            project_id=project_id,
            project_code=project_code,
        )
        if error:
            return None, error
        if project is None:
            return None, "Projeto não encontrado."
        if project.is_deleted:
            return None, "Não é permitido alterar projeto já soft-deletado."

        if "name" in normalized_changes:
            project.name = str(normalized_changes["name"]).strip()
        if "description" in normalized_changes:
            project.description = str(normalized_changes["description"]).strip() or None
        responsible_value = (
            normalized_changes.get("responsible_name")
            if "responsible_name" in normalized_changes
            else normalized_changes.get("responsible", normalized_changes.get("owner"))
        )
        if any(key in normalized_changes for key in ("responsible_name", "responsible", "owner")):
            project.owner = str(responsible_value).strip() or None
        if "status" in normalized_changes:
            project.status = str(normalized_changes["status"]).strip() or project.status
        if "notes" in normalized_changes:
            project.notes = str(normalized_changes["notes"]).strip() or None
        if "priority" in normalized_changes:
            project.priority = str(normalized_changes["priority"]).strip() or project.priority
        if "okr_links" in normalized_changes:
            try:
                project.okr_links = ProjectMCPService._normalize_okr_links(
                    normalized_changes.get("okr_links"),
                    company_id=int(company_id),
                )
            except ValueError as exc:
                return None, str(exc)

        if "start_date" in normalized_changes:
            parsed_start_date, start_date_error = ProjectTaskService.parse_due_date(normalized_changes.get("start_date"))
            if start_date_error:
                return None, start_date_error
            project.start_date = parsed_start_date

        due_value = None
        if "due_date" in normalized_changes:
            due_value = normalized_changes.get("due_date")
        elif "end_date" in normalized_changes:
            due_value = normalized_changes.get("end_date")
        elif "deadline" in normalized_changes:
            due_value = normalized_changes.get("deadline")
        if due_value is not None:
            parsed_due_date, due_date_error = ProjectTaskService.parse_due_date(due_value)
            if due_date_error:
                return None, due_date_error
            project.end_date = parsed_due_date

        if project.start_date and project.end_date and project.end_date < project.start_date:
            return None, "due_date não pode ser menor que start_date."

        db.session.commit()
        return {"project": ProjectMCPService._serialize_project(project)}, None

    @staticmethod
    def soft_delete_project(
        *,
        company_id: int,
        user_id: int,
        reason: str,
        project_id: int | None = None,
        project_code: str | None = None,
    ) -> tuple[dict[str, Any] | None, str | None]:
        project, error = ProjectMCPService.get_project(
            company_id=company_id,
            project_id=project_id,
            project_code=project_code,
            include_deleted=True,
        )
        if error:
            return None, error
        if project is None:
            return None, "Projeto não encontrado."
        if project.is_deleted:
            return None, "Projeto já está removido logicamente."

        project.is_deleted = True
        project.deleted_at = datetime.utcnow()
        project.deleted_by_user_id = int(user_id)
        project.delete_reason = str(reason or "").strip() or "soft delete via MCP"
        db.session.commit()
        return {"project": ProjectMCPService._serialize_project(project)}, None
