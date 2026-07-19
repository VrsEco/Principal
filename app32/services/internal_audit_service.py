from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from models import db
from models.employee import Employee
from models.internal_audit import (
    AUDIT_AUDITOR_ROLES,
    AUDIT_CHECKLIST_TYPES,
    AUDIT_ITEM_STATUSES,
    AUDIT_POINT_ORIGINS,
    AUDIT_POINT_STATUSES,
    AUDIT_SEVERITIES,
    AuditArea,
    AuditAuditor,
    AuditChecklist,
    AuditChecklistItem,
    AuditExecution,
    AuditExecutionItem,
    AuditPoint,
)
from models.user import User


class InternalAuditServiceError(ValueError):
    pass


def _clean_text(value: Any, *, max_length: int | None = None) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    if max_length and len(text) > max_length:
        return text[:max_length]
    return text


def _bool(value: Any, default: bool = True) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "sim", "on", "active"}


@dataclass(frozen=True)
class InternalAuditCatalogSummary:
    areas_count: int
    auditors_count: int
    checklists_count: int
    checklist_items_count: int
    executions_count: int
    open_points_count: int

    def to_dict(self) -> dict:
        return {
            "areas_count": self.areas_count,
            "auditors_count": self.auditors_count,
            "checklists_count": self.checklists_count,
            "checklist_items_count": self.checklist_items_count,
            "executions_count": self.executions_count,
            "open_points_count": self.open_points_count,
        }


class InternalAuditService:
    @staticmethod
    def summary(company_id: int) -> dict:
        return InternalAuditCatalogSummary(
            areas_count=AuditArea.query.filter_by(company_id=company_id, active=True).count(),
            auditors_count=AuditAuditor.query.filter_by(company_id=company_id, active=True).count(),
            checklists_count=AuditChecklist.query.filter_by(company_id=company_id, active=True).count(),
            checklist_items_count=AuditChecklistItem.query.filter_by(company_id=company_id, active=True).count(),
            executions_count=AuditExecution.query.filter_by(company_id=company_id).count(),
            open_points_count=AuditPoint.query.filter_by(company_id=company_id, status="open").count(),
        ).to_dict()

    @staticmethod
    def is_auditor(company_id: int, user_id: int | None, roles: set[str] | None = None) -> bool:
        if not company_id or not user_id:
            return False
        query = AuditAuditor.query.filter_by(company_id=company_id, user_id=user_id, active=True)
        if roles:
            query = query.filter(AuditAuditor.role.in_(roles))
        return query.first() is not None

    @staticmethod
    def list_areas(company_id: int, include_inactive: bool = False) -> list[dict]:
        query = AuditArea.query.filter_by(company_id=company_id)
        if not include_inactive:
            query = query.filter_by(active=True)
        return [area.to_dict() for area in query.order_by(AuditArea.name.asc()).all()]

    @staticmethod
    def create_area(company_id: int, payload: dict) -> dict:
        name = _clean_text(payload.get("name"), max_length=180)
        if not name:
            raise InternalAuditServiceError("Nome da área é obrigatório.")
        existing = AuditArea.query.filter_by(company_id=company_id, name=name).first()
        if existing:
            raise InternalAuditServiceError("Já existe uma área de auditoria com esse nome.")
        area = AuditArea(
            company_id=company_id,
            name=name,
            description=_clean_text(payload.get("description")),
            manager_user_id=payload.get("manager_user_id") or None,
            active=_bool(payload.get("active"), True),
        )
        db.session.add(area)
        db.session.commit()
        return area.to_dict()

    @staticmethod
    def list_auditors(company_id: int, include_inactive: bool = False) -> list[dict]:
        query = AuditAuditor.query.filter_by(company_id=company_id)
        if not include_inactive:
            query = query.filter_by(active=True)
        return [auditor.to_dict() for auditor in query.order_by(AuditAuditor.role.asc(), AuditAuditor.id.asc()).all()]

    @staticmethod
    def create_auditor(company_id: int, payload: dict) -> dict:
        user_id = payload.get("user_id")
        if not user_id:
            raise InternalAuditServiceError("Usuário do auditor é obrigatório.")
        role = _clean_text(payload.get("role"), max_length=40) or "auditor"
        if role not in AUDIT_AUDITOR_ROLES:
            raise InternalAuditServiceError("Perfil de auditor inválido.")
        user = User.query.get(user_id)
        if not user:
            raise InternalAuditServiceError("Usuário não encontrado.")
        employee_id = payload.get("employee_id") or None
        if not employee_id:
            employee = Employee.query.filter_by(company_id=company_id, user_id=user_id, status="active").first()
            employee_id = employee.id if employee else None
        existing = AuditAuditor.query.filter_by(company_id=company_id, user_id=user_id).first()
        if existing:
            existing.employee_id = employee_id
            existing.role = role
            existing.active = _bool(payload.get("active"), True)
            db.session.commit()
            return existing.to_dict()
        auditor = AuditAuditor(
            company_id=company_id,
            user_id=user_id,
            employee_id=employee_id,
            role=role,
            active=_bool(payload.get("active"), True),
        )
        db.session.add(auditor)
        db.session.commit()
        return auditor.to_dict()

    @staticmethod
    def list_checklists(company_id: int, include_inactive: bool = False) -> list[dict]:
        query = AuditChecklist.query.filter_by(company_id=company_id)
        if not include_inactive:
            query = query.filter_by(active=True)
        return [
            checklist.to_dict(include_items=False)
            for checklist in query.order_by(AuditChecklist.updated_at.desc(), AuditChecklist.id.desc()).all()
        ]

    @staticmethod
    def get_checklist(company_id: int, checklist_id: int) -> dict:
        checklist = AuditChecklist.query.filter_by(company_id=company_id, id=checklist_id).first()
        if not checklist:
            raise InternalAuditServiceError("Checklist não encontrado.")
        return checklist.to_dict(include_items=True)

    @staticmethod
    def create_checklist(company_id: int, payload: dict) -> dict:
        title = _clean_text(payload.get("title"), max_length=255)
        if not title:
            raise InternalAuditServiceError("Título do checklist é obrigatório.")
        checklist_type = _clean_text(payload.get("checklist_type"), max_length=30) or "autonomous"
        if checklist_type not in AUDIT_CHECKLIST_TYPES:
            raise InternalAuditServiceError("Tipo de checklist inválido.")
        checklist = AuditChecklist(
            company_id=company_id,
            title=title,
            description=_clean_text(payload.get("description")),
            checklist_type=checklist_type,
            linked_process_id=payload.get("linked_process_id") or None,
            linked_project_id=payload.get("linked_project_id") or None,
            linked_routine_id=payload.get("linked_routine_id") or None,
            area_id=payload.get("area_id") or None,
            owner_user_id=payload.get("owner_user_id") or None,
            default_periodicity=_clean_text(payload.get("default_periodicity"), max_length=60),
            active=_bool(payload.get("active"), True),
            metadata_json=payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {},
        )
        db.session.add(checklist)
        db.session.commit()
        return checklist.to_dict(include_items=True)

    @staticmethod
    def create_checklist_item(company_id: int, checklist_id: int, payload: dict) -> dict:
        checklist = AuditChecklist.query.filter_by(company_id=company_id, id=checklist_id).first()
        if not checklist:
            raise InternalAuditServiceError("Checklist não encontrado.")
        title = _clean_text(payload.get("title"), max_length=255)
        if not title:
            raise InternalAuditServiceError("Título do item é obrigatório.")
        description_for_report = _clean_text(payload.get("description_for_report"))
        if not description_for_report:
            raise InternalAuditServiceError("Descrição para relatório é obrigatória.")
        item = AuditChecklistItem(
            company_id=company_id,
            checklist_id=checklist.id,
            title=title,
            description_for_report=description_for_report,
            expected_evidence=_clean_text(payload.get("expected_evidence")),
            criterion=_clean_text(payload.get("criterion")),
            weight=payload.get("weight") or None,
            sort_order=payload.get("sort_order") or 100,
            active=_bool(payload.get("active"), True),
            metadata_json=payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {},
        )
        db.session.add(item)
        db.session.commit()
        return item.to_dict()

    @staticmethod
    def list_candidate_users(company_id: int) -> list[dict]:
        employees = (
            Employee.query.filter_by(company_id=company_id, status="active")
            .order_by(Employee.name.asc())
            .all()
        )
        result = []
        seen = set()
        for employee in employees:
            if not employee.user_id or employee.user_id in seen:
                continue
            seen.add(employee.user_id)
            result.append(
                {
                    "user_id": employee.user_id,
                    "employee_id": employee.id,
                    "name": employee.name,
                    "email": employee.email,
                }
            )
        return result

    @staticmethod
    def _parse_date(value: Any) -> date | None:
        if isinstance(value, date):
            return value
        text = _clean_text(value, max_length=20)
        if not text:
            return None
        try:
            return date.fromisoformat(text)
        except ValueError as exc:
            raise InternalAuditServiceError(f"Data inválida: {text}.") from exc

    @staticmethod
    def list_executions(company_id: int) -> list[dict]:
        return [
            execution.to_dict(include_items=False)
            for execution in AuditExecution.query.filter_by(company_id=company_id)
            .order_by(AuditExecution.updated_at.desc(), AuditExecution.id.desc())
            .all()
        ]

    @staticmethod
    def get_execution(company_id: int, execution_id: int) -> dict:
        execution = AuditExecution.query.filter_by(company_id=company_id, id=execution_id).first()
        if not execution:
            raise InternalAuditServiceError("Execução de auditoria não encontrada.")
        return execution.to_dict(include_items=True)

    @staticmethod
    def create_execution(company_id: int, payload: dict, *, current_user_id: int | None = None) -> dict:
        checklist_id = payload.get("checklist_id")
        if not checklist_id:
            raise InternalAuditServiceError("Checklist é obrigatório para abrir execução.")
        checklist = AuditChecklist.query.filter_by(company_id=company_id, id=checklist_id, active=True).first()
        if not checklist:
            raise InternalAuditServiceError("Checklist não encontrado.")
        active_items = [item for item in checklist.items if item.active]
        if not active_items:
            raise InternalAuditServiceError("Checklist precisa possuir ao menos um item ativo.")
        execution = AuditExecution(
            company_id=company_id,
            checklist_id=checklist.id,
            schedule_id=payload.get("schedule_id") or None,
            area_id=payload.get("area_id") or checklist.area_id,
            auditor_user_id=payload.get("auditor_user_id") or current_user_id,
            period_label=_clean_text(payload.get("period_label"), max_length=120),
            planned_start_date=InternalAuditService._parse_date(payload.get("planned_start_date")),
            planned_end_date=InternalAuditService._parse_date(payload.get("planned_end_date")),
            started_at=datetime.utcnow(),
            status="in_progress",
            metadata_json=payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {},
        )
        db.session.add(execution)
        db.session.flush()
        for checklist_item in active_items:
            db.session.add(
                AuditExecutionItem(
                    company_id=company_id,
                    execution_id=execution.id,
                    checklist_item_id=checklist_item.id,
                    status="not_tested",
                )
            )
        db.session.commit()
        return execution.to_dict(include_items=True)

    @staticmethod
    def update_execution_item(company_id: int, execution_item_id: int, payload: dict, *, current_user_id: int | None = None) -> dict:
        execution_item = AuditExecutionItem.query.filter_by(company_id=company_id, id=execution_item_id).first()
        if not execution_item:
            raise InternalAuditServiceError("Item da execução não encontrado.")
        status = _clean_text(payload.get("status"), max_length=40) or execution_item.status
        if status not in AUDIT_ITEM_STATUSES:
            raise InternalAuditServiceError("Status do item de auditoria inválido.")
        justification = _clean_text(payload.get("justification"))
        if status == "not_applicable" and not justification and not execution_item.justification:
            raise InternalAuditServiceError("Não aplicável exige justificativa.")
        execution_item.status = status
        execution_item.justification = justification
        execution_item.comments = _clean_text(payload.get("comments"))
        execution_item.updated_at = datetime.utcnow()
        point = None
        if status in {"qualified_conforming", "non_conforming"}:
            point = InternalAuditService._ensure_point_for_execution_item(
                company_id,
                execution_item,
                current_user_id=current_user_id,
            )
            execution_item.audit_point_id = point.id
        db.session.commit()
        result = execution_item.to_dict()
        if point:
            result["audit_point"] = point.to_dict()
        return result

    @staticmethod
    def _ensure_point_for_execution_item(
        company_id: int,
        execution_item: AuditExecutionItem,
        *,
        current_user_id: int | None = None,
    ) -> AuditPoint:
        if execution_item.audit_point_id:
            existing = AuditPoint.query.filter_by(company_id=company_id, id=execution_item.audit_point_id).first()
            if existing:
                return existing
        checklist_item = execution_item.checklist_item
        severity = "high" if execution_item.status == "non_conforming" else "medium"
        title = f"Ponto de auditoria: {getattr(checklist_item, 'title', None) or 'Item auditado'}"
        description_parts = [
            getattr(checklist_item, "description_for_report", None),
            f"Status identificado: {execution_item.status}.",
            execution_item.comments,
        ]
        point = AuditPoint(
            company_id=company_id,
            title=title[:255],
            description="\n\n".join([part for part in description_parts if part]),
            origin_type="checklist",
            source_module="audit",
            subject_type="audit_execution_item",
            subject_id=execution_item.id,
            severity=severity,
            status="open",
            assigned_to_user_id=current_user_id,
            metadata_json={
                "execution_id": execution_item.execution_id,
                "checklist_item_id": execution_item.checklist_item_id,
                "item_status": execution_item.status,
            },
        )
        db.session.add(point)
        db.session.flush()
        return point

    @staticmethod
    def list_points(company_id: int, status: str | None = None) -> list[dict]:
        query = AuditPoint.query.filter_by(company_id=company_id)
        if status:
            query = query.filter_by(status=status)
        return [
            point.to_dict()
            for point in query.order_by(AuditPoint.detected_at.desc(), AuditPoint.id.desc()).all()
        ]

    @staticmethod
    def get_point(company_id: int, point_id: int) -> dict:
        point = AuditPoint.query.filter_by(company_id=company_id, id=point_id).first()
        if not point:
            raise InternalAuditServiceError("Ponto de auditoria não encontrado.")
        return point.to_dict()

    @staticmethod
    def create_point(company_id: int, payload: dict, *, current_user_id: int | None = None) -> dict:
        title = _clean_text(payload.get("title"), max_length=255)
        if not title:
            raise InternalAuditServiceError("Título do ponto de auditoria é obrigatório.")
        origin_type = _clean_text(payload.get("origin_type"), max_length=30) or "manual"
        if origin_type not in AUDIT_POINT_ORIGINS:
            raise InternalAuditServiceError("Origem do ponto de auditoria inválida.")
        severity = _clean_text(payload.get("severity"), max_length=30) or "medium"
        if severity not in AUDIT_SEVERITIES:
            raise InternalAuditServiceError("Severidade inválida.")
        point = AuditPoint(
            company_id=company_id,
            title=title,
            description=_clean_text(payload.get("description")),
            origin_type=origin_type,
            source_module=_clean_text(payload.get("source_module"), max_length=60) or "audit",
            subject_type=_clean_text(payload.get("subject_type"), max_length=80),
            subject_id=payload.get("subject_id") or None,
            severity=severity,
            status="open",
            assigned_to_user_id=payload.get("assigned_to_user_id") or current_user_id,
            due_date=InternalAuditService._parse_date(payload.get("due_date")),
            metadata_json=payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {},
        )
        db.session.add(point)
        db.session.commit()
        return point.to_dict()

    @staticmethod
    def update_point(company_id: int, point_id: int, payload: dict) -> dict:
        point = AuditPoint.query.filter_by(company_id=company_id, id=point_id).first()
        if not point:
            raise InternalAuditServiceError("Ponto de auditoria não encontrado.")
        status = _clean_text(payload.get("status"), max_length=40)
        if status:
            if status not in AUDIT_POINT_STATUSES:
                raise InternalAuditServiceError("Status do ponto de auditoria inválido.")
            point.status = status
        severity = _clean_text(payload.get("severity"), max_length=30)
        if severity:
            if severity not in AUDIT_SEVERITIES:
                raise InternalAuditServiceError("Severidade inválida.")
            point.severity = severity
        if "description" in payload:
            point.description = _clean_text(payload.get("description"))
        if "assigned_to_user_id" in payload:
            point.assigned_to_user_id = payload.get("assigned_to_user_id") or None
        if "due_date" in payload:
            point.due_date = InternalAuditService._parse_date(payload.get("due_date"))
        point.updated_at = datetime.utcnow()
        db.session.commit()
        return point.to_dict()
