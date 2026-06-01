from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from models import db
from models.employee import Employee
from models.internal_audit import (
    AUDIT_AUDITOR_ROLES,
    AUDIT_CHECKLIST_TYPES,
    AuditArea,
    AuditAuditor,
    AuditChecklist,
    AuditChecklistItem,
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

    def to_dict(self) -> dict:
        return {
            "areas_count": self.areas_count,
            "auditors_count": self.auditors_count,
            "checklists_count": self.checklists_count,
            "checklist_items_count": self.checklist_items_count,
        }


class InternalAuditService:
    @staticmethod
    def summary(company_id: int) -> dict:
        return InternalAuditCatalogSummary(
            areas_count=AuditArea.query.filter_by(company_id=company_id, active=True).count(),
            auditors_count=AuditAuditor.query.filter_by(company_id=company_id, active=True).count(),
            checklists_count=AuditChecklist.query.filter_by(company_id=company_id, active=True).count(),
            checklist_items_count=AuditChecklistItem.query.filter_by(company_id=company_id, active=True).count(),
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
