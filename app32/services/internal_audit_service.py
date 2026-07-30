from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from models import db
from models.employee import Employee
from models.internal_audit import (
    AUDIT_AUDITOR_ROLES,
    AUDIT_CHECKLIST_TYPES,
    AUDIT_EVIDENCE_TYPES,
    AUDIT_FINDING_STATUSES,
    AUDIT_FOLLOW_UP_STATUSES,
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
    AuditEvidenceLink,
    AuditFinding,
    AuditFollowUp,
    AuditPoint,
    AuditReport,
    AuditWorkpaper,
)
from models.meeting import Meeting
from models.project import Project, ProjectTask
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


def _int_or_none(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise InternalAuditServiceError("Identificador inválido.") from exc


@dataclass(frozen=True)
class InternalAuditCatalogSummary:
    areas_count: int
    auditors_count: int
    checklists_count: int
    checklist_items_count: int
    executions_count: int
    open_points_count: int
    workpapers_count: int
    findings_count: int
    open_findings_count: int
    reports_count: int
    pending_follow_ups_count: int

    def to_dict(self) -> dict:
        return {
            "areas_count": self.areas_count,
            "auditors_count": self.auditors_count,
            "checklists_count": self.checklists_count,
            "checklist_items_count": self.checklist_items_count,
            "executions_count": self.executions_count,
            "open_points_count": self.open_points_count,
            "workpapers_count": self.workpapers_count,
            "findings_count": self.findings_count,
            "open_findings_count": self.open_findings_count,
            "reports_count": self.reports_count,
            "pending_follow_ups_count": self.pending_follow_ups_count,
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
            workpapers_count=AuditWorkpaper.query.filter_by(company_id=company_id).count(),
            findings_count=AuditFinding.query.filter_by(company_id=company_id).count(),
            open_findings_count=AuditFinding.query.filter(
                AuditFinding.company_id == company_id,
                AuditFinding.status.in_(("open", "action_linked", "in_follow_up")),
            ).count(),
            reports_count=AuditReport.query.filter_by(company_id=company_id).count(),
            pending_follow_ups_count=AuditFinding.query.filter(
                AuditFinding.company_id == company_id,
                AuditFinding.status.in_(("open", "action_linked", "in_follow_up", "resolved")),
            ).count(),
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

    @staticmethod
    def list_workpapers(company_id: int) -> list[dict]:
        return [
            workpaper.to_dict(include_evidences=False)
            for workpaper in AuditWorkpaper.query.filter_by(company_id=company_id)
            .order_by(AuditWorkpaper.updated_at.desc(), AuditWorkpaper.id.desc())
            .all()
        ]

    @staticmethod
    def get_workpaper(company_id: int, workpaper_id: int) -> dict:
        workpaper = AuditWorkpaper.query.filter_by(company_id=company_id, id=workpaper_id).first()
        if not workpaper:
            raise InternalAuditServiceError("Papel de trabalho não encontrado.")
        return workpaper.to_dict(include_evidences=True)

    @staticmethod
    def create_workpaper(company_id: int, payload: dict, *, current_user_id: int | None = None) -> dict:
        execution_id = _int_or_none(payload.get("execution_id"))
        execution_item_id = _int_or_none(payload.get("execution_item_id"))
        audit_point_id = _int_or_none(payload.get("audit_point_id"))
        if not any([execution_id, execution_item_id, audit_point_id]):
            raise InternalAuditServiceError("Informe execução, item executado ou ponto de auditoria.")

        if execution_id and not AuditExecution.query.filter_by(company_id=company_id, id=execution_id).first():
            raise InternalAuditServiceError("Execução de auditoria não encontrada.")
        if execution_item_id:
            item = AuditExecutionItem.query.filter_by(company_id=company_id, id=execution_item_id).first()
            if not item:
                raise InternalAuditServiceError("Item da execução não encontrado.")
            execution_id = execution_id or item.execution_id
            audit_point_id = audit_point_id or item.audit_point_id
        if audit_point_id and not AuditPoint.query.filter_by(company_id=company_id, id=audit_point_id).first():
            raise InternalAuditServiceError("Ponto de auditoria não encontrado.")

        workpaper = AuditWorkpaper(
            company_id=company_id,
            execution_id=execution_id,
            execution_item_id=execution_item_id,
            audit_point_id=audit_point_id,
            auditor_user_id=_int_or_none(payload.get("auditor_user_id")) or current_user_id,
            comments=_clean_text(payload.get("comments")),
            conclusion=_clean_text(payload.get("conclusion")),
            alert_notes=_clean_text(payload.get("alert_notes")),
            evidence_summary=_clean_text(payload.get("evidence_summary")),
            metadata_json=payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {},
        )
        db.session.add(workpaper)
        db.session.commit()
        return workpaper.to_dict(include_evidences=True)

    @staticmethod
    def list_findings(company_id: int, status: str | None = None) -> list[dict]:
        query = AuditFinding.query.filter_by(company_id=company_id)
        if status:
            query = query.filter_by(status=status)
        return [
            finding.to_dict(include_evidences=False)
            for finding in query.order_by(AuditFinding.updated_at.desc(), AuditFinding.id.desc()).all()
        ]

    @staticmethod
    def get_finding(company_id: int, finding_id: int) -> dict:
        finding = AuditFinding.query.filter_by(company_id=company_id, id=finding_id).first()
        if not finding:
            raise InternalAuditServiceError("Achado de auditoria não encontrado.")
        return finding.to_dict(include_evidences=True)

    @staticmethod
    def create_finding(company_id: int, payload: dict, *, current_user_id: int | None = None) -> dict:
        audit_point_id = _int_or_none(payload.get("audit_point_id"))
        point = None
        if audit_point_id:
            point = AuditPoint.query.filter_by(company_id=company_id, id=audit_point_id).first()
            if not point:
                raise InternalAuditServiceError("Ponto de auditoria não encontrado.")

        title = _clean_text(payload.get("title"), max_length=255) or (point.title if point else None)
        if not title:
            raise InternalAuditServiceError("Título do achado é obrigatório.")
        severity = _clean_text(payload.get("severity"), max_length=30) or (point.severity if point else "medium")
        if severity not in AUDIT_SEVERITIES:
            raise InternalAuditServiceError("Severidade inválida.")

        execution_id = _int_or_none(payload.get("execution_id"))
        execution_item_id = _int_or_none(payload.get("execution_item_id"))
        if point and point.subject_type == "audit_execution_item" and point.subject_id:
            execution_item = AuditExecutionItem.query.filter_by(company_id=company_id, id=point.subject_id).first()
            if execution_item:
                execution_item_id = execution_item_id or execution_item.id
                execution_id = execution_id or execution_item.execution_id

        finding = AuditFinding(
            company_id=company_id,
            audit_point_id=audit_point_id,
            execution_id=execution_id,
            execution_item_id=execution_item_id,
            title=title,
            condition_text=_clean_text(payload.get("condition_text")) or (point.description if point else None),
            criterion_text=_clean_text(payload.get("criterion_text")),
            cause_text=_clean_text(payload.get("cause_text")),
            effect_text=_clean_text(payload.get("effect_text")),
            recommendation_text=_clean_text(payload.get("recommendation_text")),
            severity=severity,
            status="open",
            responsible_user_id=_int_or_none(payload.get("responsible_user_id")) or current_user_id,
            due_date=InternalAuditService._parse_date(payload.get("due_date")),
            metadata_json=payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {},
        )
        db.session.add(finding)
        if point:
            point.status = "converted_to_finding"
            point.updated_at = datetime.utcnow()
        db.session.commit()
        return finding.to_dict(include_evidences=True)

    @staticmethod
    def update_finding(company_id: int, finding_id: int, payload: dict) -> dict:
        finding = AuditFinding.query.filter_by(company_id=company_id, id=finding_id).first()
        if not finding:
            raise InternalAuditServiceError("Achado de auditoria não encontrado.")

        status = _clean_text(payload.get("status"), max_length=40)
        if status:
            if status not in AUDIT_FINDING_STATUSES:
                raise InternalAuditServiceError("Status do achado inválido.")
            finding.status = status
        severity = _clean_text(payload.get("severity"), max_length=30)
        if severity:
            if severity not in AUDIT_SEVERITIES:
                raise InternalAuditServiceError("Severidade inválida.")
            finding.severity = severity

        for field in (
            "title",
            "condition_text",
            "criterion_text",
            "cause_text",
            "effect_text",
            "recommendation_text",
        ):
            if field in payload:
                value = _clean_text(payload.get(field), max_length=255) if field == "title" else _clean_text(payload.get(field))
                if field == "title" and not value:
                    raise InternalAuditServiceError("Título do achado é obrigatório.")
                setattr(finding, field, value)

        if "responsible_user_id" in payload:
            finding.responsible_user_id = _int_or_none(payload.get("responsible_user_id"))
        if "due_date" in payload:
            finding.due_date = InternalAuditService._parse_date(payload.get("due_date"))
        if "project_id" in payload:
            finding.project_id = InternalAuditService._validate_project_link(company_id, payload.get("project_id"))
        if "task_id" in payload:
            finding.task_id = InternalAuditService._validate_task_link(company_id, payload.get("task_id"), finding.project_id)
        if "alignment_meeting_id" in payload:
            finding.alignment_meeting_id = InternalAuditService._validate_meeting_link(company_id, payload.get("alignment_meeting_id"))

        if finding.status == "open" and (finding.project_id or finding.task_id):
            finding.status = "action_linked"
        finding.updated_at = datetime.utcnow()
        db.session.commit()
        return finding.to_dict(include_evidences=True)

    @staticmethod
    def create_evidence_link(company_id: int, payload: dict, *, current_user_id: int | None = None) -> dict:
        workpaper_id = _int_or_none(payload.get("workpaper_id"))
        finding_id = _int_or_none(payload.get("finding_id"))
        if not workpaper_id and not finding_id:
            raise InternalAuditServiceError("Informe papel de trabalho ou achado.")
        if workpaper_id and not AuditWorkpaper.query.filter_by(company_id=company_id, id=workpaper_id).first():
            raise InternalAuditServiceError("Papel de trabalho não encontrado.")
        if finding_id and not AuditFinding.query.filter_by(company_id=company_id, id=finding_id).first():
            raise InternalAuditServiceError("Achado de auditoria não encontrado.")
        evidence_type = _clean_text(payload.get("evidence_type"), max_length=30) or "comment"
        if evidence_type not in AUDIT_EVIDENCE_TYPES:
            raise InternalAuditServiceError("Tipo de evidência inválido.")
        evidence = AuditEvidenceLink(
            company_id=company_id,
            workpaper_id=workpaper_id,
            finding_id=finding_id,
            evidence_type=evidence_type,
            source_module=_clean_text(payload.get("source_module"), max_length=60),
            source_id=_int_or_none(payload.get("source_id")),
            file_path=_clean_text(payload.get("file_path")),
            caption=_clean_text(payload.get("caption")),
            created_by_user_id=current_user_id,
        )
        db.session.add(evidence)
        db.session.commit()
        return evidence.to_dict()

    @staticmethod
    def _validate_project_link(company_id: int, project_id: Any) -> int | None:
        project_id = _int_or_none(project_id)
        if not project_id:
            return None
        project = Project.query.filter_by(company_id=company_id, id=project_id, is_deleted=False).first()
        if not project:
            raise InternalAuditServiceError("Projeto não encontrado para a empresa ativa.")
        return project.id

    @staticmethod
    def _validate_task_link(company_id: int, task_id: Any, project_id: int | None = None) -> int | None:
        task_id = _int_or_none(task_id)
        if not task_id:
            return None
        query = ProjectTask.query.join(Project, Project.id == ProjectTask.project_id).filter(
            Project.company_id == company_id,
            ProjectTask.id == task_id,
            ProjectTask.is_deleted.is_(False),
            Project.is_deleted.is_(False),
        )
        if project_id:
            query = query.filter(ProjectTask.project_id == project_id)
        task = query.first()
        if not task:
            raise InternalAuditServiceError("Atividade não encontrada para a empresa ativa.")
        return task.id

    @staticmethod
    def _validate_meeting_link(company_id: int, meeting_id: Any) -> int | None:
        meeting_id = _int_or_none(meeting_id)
        if not meeting_id:
            return None
        meeting = Meeting.query.filter_by(company_id=company_id, id=meeting_id).first()
        if not meeting:
            raise InternalAuditServiceError("Reunião de alinhamento não encontrada para a empresa ativa.")
        return meeting.id

    @staticmethod
    def list_reports(company_id: int) -> list[dict]:
        return [
            report.to_dict(include_snapshot=False)
            for report in AuditReport.query.filter_by(company_id=company_id)
            .order_by(AuditReport.updated_at.desc(), AuditReport.id.desc())
            .all()
        ]

    @staticmethod
    def get_report(company_id: int, report_id: int) -> dict:
        report = AuditReport.query.filter_by(company_id=company_id, id=report_id).first()
        if not report:
            raise InternalAuditServiceError("Relatório de auditoria não encontrado.")
        return report.to_dict(include_snapshot=True)

    @staticmethod
    def create_report(company_id: int, payload: dict, *, current_user_id: int | None = None) -> dict:
        execution_id = _int_or_none(payload.get("execution_id"))
        if not execution_id:
            raise InternalAuditServiceError("Execução de auditoria é obrigatória.")
        execution = AuditExecution.query.filter_by(company_id=company_id, id=execution_id).first()
        if not execution:
            raise InternalAuditServiceError("Execução de auditoria não encontrada.")

        latest = (
            AuditReport.query.filter_by(company_id=company_id, execution_id=execution.id)
            .order_by(AuditReport.version.desc())
            .first()
        )
        version = (latest.version + 1) if latest else 1
        default_title = f"Relatório de Auditoria — {getattr(execution.checklist, 'title', '') or execution.id}"
        report = AuditReport(
            company_id=company_id,
            execution_id=execution.id,
            version=version,
            supersedes_report_id=latest.id if latest else None,
            title=_clean_text(payload.get("title"), max_length=255) or default_title[:255],
            objective=_clean_text(payload.get("objective")),
            scope_text=_clean_text(payload.get("scope_text")),
            period_start=InternalAuditService._parse_date(payload.get("period_start")) or execution.planned_start_date,
            period_end=InternalAuditService._parse_date(payload.get("period_end")) or execution.planned_end_date,
            executive_summary=_clean_text(payload.get("executive_summary")),
            auditor_conclusion=_clean_text(payload.get("auditor_conclusion")),
            opinion=_clean_text(payload.get("opinion"), max_length=80),
            status="draft",
            snapshot_json={},
            prepared_by_user_id=current_user_id,
        )
        db.session.add(report)
        db.session.commit()
        return report.to_dict(include_snapshot=True)

    @staticmethod
    def update_report(company_id: int, report_id: int, payload: dict) -> dict:
        report = AuditReport.query.filter_by(company_id=company_id, id=report_id).first()
        if not report:
            raise InternalAuditServiceError("Relatório de auditoria não encontrado.")
        if report.status != "draft":
            raise InternalAuditServiceError("Relatório emitido é imutável; crie uma nova versão.")

        for field in ("title", "objective", "scope_text", "executive_summary", "auditor_conclusion", "opinion"):
            if field in payload:
                value = _clean_text(payload.get(field), max_length=255 if field == "title" else None)
                if field == "title" and not value:
                    raise InternalAuditServiceError("Título do relatório é obrigatório.")
                setattr(report, field, value)
        if "period_start" in payload:
            report.period_start = InternalAuditService._parse_date(payload.get("period_start"))
        if "period_end" in payload:
            report.period_end = InternalAuditService._parse_date(payload.get("period_end"))
        report.updated_at = datetime.utcnow()
        db.session.commit()
        return report.to_dict(include_snapshot=True)

    @staticmethod
    def issue_report(company_id: int, report_id: int, *, current_user_id: int | None = None) -> dict:
        report = AuditReport.query.filter_by(company_id=company_id, id=report_id).first()
        if not report:
            raise InternalAuditServiceError("Relatório de auditoria não encontrado.")
        if report.status != "draft":
            raise InternalAuditServiceError("Somente relatório em rascunho pode ser emitido.")
        if not report.auditor_conclusion:
            raise InternalAuditServiceError("Conclusão do auditor é obrigatória para emissão.")

        execution = AuditExecution.query.filter_by(company_id=company_id, id=report.execution_id).first()
        if not execution:
            raise InternalAuditServiceError("Execução vinculada não encontrada.")

        previous_issued = (
            AuditReport.query.filter(
                AuditReport.company_id == company_id,
                AuditReport.execution_id == execution.id,
                AuditReport.id != report.id,
                AuditReport.status == "issued",
            )
            .order_by(AuditReport.version.desc())
            .first()
        )
        now = datetime.utcnow()
        if previous_issued:
            previous_issued.status = "superseded"
            previous_issued.updated_at = now
            report.supersedes_report_id = previous_issued.id

        report.snapshot_json = InternalAuditService._build_report_snapshot(company_id, execution)
        report.status = "issued"
        report.approved_by_user_id = current_user_id
        report.approved_at = now
        report.issued_at = now
        report.updated_at = now
        db.session.commit()
        return report.to_dict(include_snapshot=True)

    @staticmethod
    def _build_report_snapshot(company_id: int, execution: AuditExecution) -> dict:
        findings = (
            AuditFinding.query.filter_by(company_id=company_id, execution_id=execution.id)
            .order_by(AuditFinding.severity.desc(), AuditFinding.id.asc())
            .all()
        )
        workpapers = (
            AuditWorkpaper.query.filter_by(company_id=company_id, execution_id=execution.id)
            .order_by(AuditWorkpaper.id.asc())
            .all()
        )
        items = execution.to_dict(include_items=True).get("items", [])
        status_counts: dict[str, int] = {}
        for item in items:
            status = item.get("status") or "not_tested"
            status_counts[status] = status_counts.get(status, 0) + 1
        return {
            "generated_at": datetime.utcnow().isoformat(),
            "execution": execution.to_dict(include_items=True),
            "findings": [finding.to_dict(include_evidences=True) for finding in findings],
            "workpapers": [workpaper.to_dict(include_evidences=True) for workpaper in workpapers],
            "summary": {
                "items_count": len(items),
                "status_counts": status_counts,
                "findings_count": len(findings),
                "open_findings_count": sum(
                    1 for finding in findings if finding.status in {"open", "action_linked", "in_follow_up"}
                ),
            },
        }

    @staticmethod
    def list_follow_ups(company_id: int, finding_id: int | None = None) -> list[dict]:
        query = AuditFollowUp.query.filter_by(company_id=company_id)
        if finding_id:
            query = query.filter_by(finding_id=finding_id)
        return [
            follow_up.to_dict()
            for follow_up in query.order_by(AuditFollowUp.created_at.desc(), AuditFollowUp.id.desc()).all()
        ]

    @staticmethod
    def create_follow_up(company_id: int, payload: dict, *, current_user_id: int | None = None) -> dict:
        finding_id = _int_or_none(payload.get("finding_id"))
        finding = AuditFinding.query.filter_by(company_id=company_id, id=finding_id).first()
        if not finding:
            raise InternalAuditServiceError("Achado de auditoria não encontrado.")
        status = _clean_text(payload.get("status"), max_length=40) or "awaiting_action"
        if status not in AUDIT_FOLLOW_UP_STATUSES:
            raise InternalAuditServiceError("Status de follow-up inválido.")
        if status in {"resolved", "closed"} and not _clean_text(payload.get("auditor_notes")):
            raise InternalAuditServiceError("Resolução ou encerramento exige validação do auditor.")

        previous_status = finding.status
        follow_up = AuditFollowUp(
            company_id=company_id,
            finding_id=finding.id,
            previous_status=previous_status,
            status=status,
            action_summary=_clean_text(payload.get("action_summary")),
            auditor_notes=_clean_text(payload.get("auditor_notes")),
            evidence_summary=_clean_text(payload.get("evidence_summary")),
            due_date=InternalAuditService._parse_date(payload.get("due_date")) or finding.due_date,
            next_review_date=InternalAuditService._parse_date(payload.get("next_review_date")),
            performed_by_user_id=current_user_id,
        )
        finding.status = {
            "awaiting_action": "action_linked" if (finding.project_id or finding.task_id) else "open",
            "in_progress": "in_follow_up",
            "awaiting_validation": "in_follow_up",
            "resolved": "resolved",
            "closed": "closed",
            "reopened": "open",
        }[status]
        finding.updated_at = datetime.utcnow()
        db.session.add(follow_up)
        db.session.commit()
        return follow_up.to_dict()
