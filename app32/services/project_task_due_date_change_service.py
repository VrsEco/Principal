import unicodedata
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Optional

from flask import has_request_context, request
from flask_login import current_user

from models import (
    CompanyPerformanceSettings,
    Employee,
    Project,
    ProjectTask,
    ProjectTaskDueDateChangeRequest,
    UserLog,
    db,
)


class ProjectTaskDueDateChangeService:
    """Regras determinísticas de gestão de adiamentos de prazo."""

    VALID_STATUSES = {"pending", "approved", "rejected", "cancelled"}
    VALID_ACTIONS = {"approve", "reject"}
    VALID_REQUEST_TYPES = {"postpone", "advance", "define", "clear"}

    @staticmethod
    def _normalize_name(value: Optional[str]) -> str:
        raw = str(value or "").strip().lower()
        normalized = unicodedata.normalize("NFKD", raw)
        return "".join(char for char in normalized if not unicodedata.combining(char))

    @staticmethod
    def _safe_date(value: Any) -> Optional[date]:
        if value is None or value == "":
            return None
        if isinstance(value, date):
            return value
        raw = str(value).strip()
        for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
            try:
                return datetime.strptime(raw, fmt).date()
            except ValueError:
                continue
        return None

    @staticmethod
    def _determine_request_type(
        old_due_date: Optional[date], requested_due_date: Optional[date]
    ) -> str:
        if old_due_date is None and requested_due_date is not None:
            return "define"
        if old_due_date is not None and requested_due_date is None:
            return "clear"
        if old_due_date and requested_due_date:
            if requested_due_date > old_due_date:
                return "postpone"
            if requested_due_date < old_due_date:
                return "advance"
        return "postpone"

    @staticmethod
    def get_or_create_company_settings(company_id: int) -> CompanyPerformanceSettings:
        settings = CompanyPerformanceSettings.query.filter_by(company_id=company_id).first()
        if settings:
            return settings
        settings = CompanyPerformanceSettings(company_id=company_id)
        db.session.add(settings)
        db.session.flush()
        return settings

    @staticmethod
    def _build_user_log(
        *,
        action: str,
        entity_id: str,
        entity_name: str,
        company_id: int,
        description: str,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not current_user.is_authenticated:
            return

        import json

        log = UserLog(
            user_id=getattr(current_user, "id", None),
            user_email=str(getattr(current_user, "email", "") or "desconhecido"),
            user_name=str(
                getattr(current_user, "name", None)
                or getattr(current_user, "username", None)
                or "Usuário"
            ),
            action=action,
            entity_type="project_task_due_date_change",
            entity_id=str(entity_id),
            entity_name=entity_name,
            old_values=json.dumps(old_values or {}, ensure_ascii=False),
            new_values=json.dumps(new_values or {}, ensure_ascii=False),
            ip_address=(request.remote_addr if has_request_context() else None),
            user_agent=(
                request.headers.get("User-Agent") if has_request_context() else None
            ),
            endpoint=(request.path if has_request_context() else None),
            method=(request.method if has_request_context() else None),
            description=description,
            company_id=company_id,
        )
        db.session.add(log)

    @staticmethod
    def get_task_or_error(
        *, company_id: int, project_id: int, task_id: int
    ) -> tuple[Optional[ProjectTask], Optional[Project], Optional[str]]:
        project = Project.query.filter_by(id=project_id, company_id=company_id).first()
        if not project:
            return None, None, "Projeto não encontrado no contexto informado."

        task = ProjectTask.query.filter_by(id=task_id, project_id=project_id).first()
        if not task:
            return None, project, "Atividade não encontrada no projeto informado."

        return task, project, None

    @staticmethod
    def user_can_approve(project: Optional[Project], company_id: Optional[int]) -> bool:
        if not current_user.is_authenticated:
            return False

        if not project or not project.owner:
            return False

        current_names = {
            ProjectTaskDueDateChangeService._normalize_name(
                getattr(current_user, "name", None)
                or getattr(current_user, "username", None)
            )
        }

        employee = (
            Employee.query.filter_by(user_id=current_user.id, company_id=company_id)
            .order_by(Employee.id.asc())
            .first()
        )
        if employee and employee.name:
            current_names.add(
                ProjectTaskDueDateChangeService._normalize_name(employee.name)
            )

        owner_name = ProjectTaskDueDateChangeService._normalize_name(project.owner)
        return owner_name != "" and owner_name in current_names

    @staticmethod
    def create_request(
        *, company_id: int, project_id: int, task_id: int, requested_due_date: Any, reason: str
    ) -> tuple[Optional[ProjectTaskDueDateChangeRequest], Optional[str]]:
        task, project, error = ProjectTaskDueDateChangeService.get_task_or_error(
            company_id=company_id,
            project_id=project_id,
            task_id=task_id,
        )
        if error:
            return None, error
        if not task or not project:
            return None, "Atividade não encontrada."

        parsed_due_date = ProjectTaskDueDateChangeService._safe_date(requested_due_date)
        if requested_due_date not in (None, "") and not parsed_due_date:
            return None, "Data solicitada inválida. Use DD/MM/AAAA ou AAAA-MM-DD."

        settings = ProjectTaskDueDateChangeService.get_or_create_company_settings(
            company_id
        )
        today = datetime.now().date()
        old_due_date = task.due_date
        was_after_due_date = bool(old_due_date and today > old_due_date)
        allow_after_due = bool(getattr(settings, "allow_postpone_after_due_date", False))

        request_type = ProjectTaskDueDateChangeService._determine_request_type(
            old_due_date, parsed_due_date
        )

        if request_type == "postpone" and was_after_due_date and not allow_after_due:
            return (
                None,
                "A política da empresa não permite adiamento após o vencimento atual.",
            )

        reason_text = str(reason or "").strip()
        if not reason_text:
            return None, "Informe o motivo da solicitação de adiamento."

        pending_request = (
            ProjectTaskDueDateChangeRequest.query.filter_by(
                company_id=company_id,
                project_id=project_id,
                task_id=task_id,
                status="pending",
            )
            .order_by(ProjectTaskDueDateChangeRequest.id.desc())
            .first()
        )
        if pending_request:
            return None, "Já existe uma solicitação pendente para esta atividade."

        request_obj = ProjectTaskDueDateChangeRequest(
            company_id=company_id,
            project_id=project_id,
            task_id=task_id,
            request_type=request_type,
            old_due_date=old_due_date,
            requested_due_date=parsed_due_date,
            reason=reason_text,
            status="pending",
            requested_by_user_id=getattr(current_user, "id", None),
            requested_by_name=(
                getattr(current_user, "name", None)
                or getattr(current_user, "username", None)
                or "Usuário"
            ),
            requested_at=datetime.utcnow(),
            was_after_due_date_when_requested=was_after_due_date,
            penalty_points=Decimal("0"),
        )
        db.session.add(request_obj)
        db.session.flush()

        ProjectTaskDueDateChangeService._build_user_log(
            action="CREATE",
            entity_id=str(request_obj.id),
            entity_name=task.what,
            company_id=company_id,
            description=(
                f"Solicitação de alteração de prazo criada para atividade {task.id}."
            ),
            old_values={
                "old_due_date": old_due_date.isoformat() if old_due_date else None,
            },
            new_values=request_obj.to_dict(),
        )
        db.session.commit()
        return request_obj, None

    @staticmethod
    def decide_request(
        *,
        company_id: int,
        project_id: int,
        task_id: int,
        request_id: int,
        action: str,
        approved_due_date: Any = None,
        approval_note: Optional[str] = None,
    ) -> tuple[Optional[ProjectTaskDueDateChangeRequest], Optional[str]]:
        if action not in ProjectTaskDueDateChangeService.VALID_ACTIONS:
            return None, "Ação inválida para solicitação de prazo."

        task, project, error = ProjectTaskDueDateChangeService.get_task_or_error(
            company_id=company_id,
            project_id=project_id,
            task_id=task_id,
        )
        if error:
            return None, error
        if not task or not project:
            return None, "Atividade não encontrada."

        request_obj = ProjectTaskDueDateChangeRequest.query.filter_by(
            id=request_id,
            company_id=company_id,
            project_id=project_id,
            task_id=task_id,
        ).first()
        if not request_obj:
            return None, "Solicitação de alteração de prazo não encontrada."
        if request_obj.status != "pending":
            return None, "A solicitação informada não está mais pendente."

        if not ProjectTaskDueDateChangeService.user_can_approve(project, company_id):
            return None, "Somente o responsável do projeto pode aprovar ou rejeitar adiamentos."

        note_text = str(approval_note or "").strip() or None
        approved_date = ProjectTaskDueDateChangeService._safe_date(approved_due_date)

        old_task_due_date = task.due_date

        if action == "approve":
            if request_obj.request_type == "clear":
                approved_date = None
            elif not approved_date:
                approved_date = request_obj.requested_due_date

            if request_obj.request_type != "clear" and not approved_date:
                return None, "Informe a data aprovada para concluir a aprovação."

            request_obj.status = "approved"
            request_obj.approved_due_date = approved_date
            request_obj.approved_by_user_id = getattr(current_user, "id", None)
            request_obj.approved_by_name = (
                getattr(current_user, "name", None)
                or getattr(current_user, "username", None)
                or "Usuário"
            )
            request_obj.approved_at = datetime.utcnow()
            request_obj.approval_note = note_text

            settings = ProjectTaskDueDateChangeService.get_or_create_company_settings(
                company_id
            )
            if request_obj.request_type == "postpone":
                request_obj.penalty_points = Decimal(
                    str(getattr(settings, "postpone_penalty_points", -1) or 0)
                )
            else:
                request_obj.penalty_points = Decimal("0")

            task.due_date = approved_date

            ProjectTaskDueDateChangeService._build_user_log(
                action="APPROVE",
                entity_id=str(request_obj.id),
                entity_name=task.what,
                company_id=company_id,
                description=(
                    f"Solicitação de alteração de prazo aprovada para atividade {task.id}."
                ),
                old_values={
                    "task_due_date": old_task_due_date.isoformat()
                    if old_task_due_date
                    else None,
                    "request_status": "pending",
                },
                new_values={
                    "task_due_date": approved_date.isoformat() if approved_date else None,
                    "request_status": "approved",
                    "penalty_points": float(request_obj.penalty_points or 0),
                },
            )
        else:
            request_obj.status = "rejected"
            request_obj.approved_by_user_id = getattr(current_user, "id", None)
            request_obj.approved_by_name = (
                getattr(current_user, "name", None)
                or getattr(current_user, "username", None)
                or "Usuário"
            )
            request_obj.approved_at = datetime.utcnow()
            request_obj.approval_note = note_text
            request_obj.penalty_points = Decimal("0")

            ProjectTaskDueDateChangeService._build_user_log(
                action="REJECT",
                entity_id=str(request_obj.id),
                entity_name=task.what,
                company_id=company_id,
                description=(
                    f"Solicitação de alteração de prazo rejeitada para atividade {task.id}."
                ),
                old_values={"request_status": "pending"},
                new_values={"request_status": "rejected"},
            )

        db.session.commit()
        return request_obj, None

    @staticmethod
    def list_requests(
        *, company_id: int, project_id: int, task_id: int
    ) -> tuple[List[ProjectTaskDueDateChangeRequest], Optional[Project], Optional[str]]:
        _, project, error = ProjectTaskDueDateChangeService.get_task_or_error(
            company_id=company_id,
            project_id=project_id,
            task_id=task_id,
        )
        if error:
            return [], project, error

        requests = (
            ProjectTaskDueDateChangeRequest.query.filter_by(
                company_id=company_id,
                project_id=project_id,
                task_id=task_id,
            )
            .order_by(
                ProjectTaskDueDateChangeRequest.requested_at.desc(),
                ProjectTaskDueDateChangeRequest.id.desc(),
            )
            .all()
        )
        return requests, project, None

    @staticmethod
    def build_task_context(task_id: int, company_id: Optional[int] = None) -> Dict[str, Any]:
        context_map = ProjectTaskDueDateChangeService.build_task_context_map(
            [task_id], company_id=company_id
        )
        return context_map.get(int(task_id or 0), ProjectTaskDueDateChangeService.empty_context())

    @staticmethod
    def empty_context() -> Dict[str, Any]:
        return {
            "postponement_summary": {
                "postponement_count": 0,
                "has_pending_request": False,
                "is_postponed": False,
                "latest_status": None,
                "latest_requested_due_date": None,
                "latest_approved_due_date": None,
            }
        }

    @staticmethod
    def build_task_context_map(
        task_ids: Iterable[int], company_id: Optional[int] = None
    ) -> Dict[int, Dict[str, Any]]:
        normalized_ids = [int(task_id) for task_id in task_ids if int(task_id or 0) > 0]
        if not normalized_ids:
            return {}

        grouped: Dict[int, Dict[str, Any]] = {
            task_id: {
                "requests": [],
                "postponement_summary": {
                    "postponement_count": 0,
                    "has_pending_request": False,
                    "is_postponed": False,
                    "latest_status": None,
                    "latest_requested_due_date": None,
                    "latest_approved_due_date": None,
                },
            }
            for task_id in normalized_ids
        }

        query = ProjectTaskDueDateChangeRequest.query.filter(
            ProjectTaskDueDateChangeRequest.task_id.in_(normalized_ids)
        )
        if company_id is not None:
            query = query.filter(
                ProjectTaskDueDateChangeRequest.company_id == company_id
            )

        rows = query.order_by(
            ProjectTaskDueDateChangeRequest.requested_at.desc(),
            ProjectTaskDueDateChangeRequest.id.desc(),
        ).all()

        for row in rows:
            task_group = grouped.setdefault(row.task_id, ProjectTaskDueDateChangeService.empty_context())
            task_group.setdefault("requests", []).append(row.to_dict())
            summary = task_group["postponement_summary"]
            if summary["latest_status"] is None:
                summary["latest_status"] = row.status
                summary["latest_requested_due_date"] = (
                    row.requested_due_date.isoformat() if row.requested_due_date else None
                )
                summary["latest_approved_due_date"] = (
                    row.approved_due_date.isoformat() if row.approved_due_date else None
                )
            if row.status == "pending":
                summary["has_pending_request"] = True
            if row.status == "approved" and row.request_type == "postpone":
                summary["postponement_count"] += 1

        for task_group in grouped.values():
            summary = task_group["postponement_summary"]
            summary["is_postponed"] = summary["postponement_count"] > 0

        return grouped
