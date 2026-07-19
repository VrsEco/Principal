from __future__ import annotations

from datetime import date, datetime

from sqlalchemy.dialects.postgresql import JSONB

from . import db

AUDIT_CHECKLIST_TYPES = ("process", "project", "autonomous")
AUDIT_AUDITOR_ROLES = ("auditor_admin", "auditor", "viewer_executivo")
AUDIT_EXECUTION_STATUSES = ("planned", "in_progress", "completed", "cancelled")
AUDIT_ITEM_STATUSES = (
    "conforming",
    "qualified_conforming",
    "non_conforming",
    "not_applicable",
    "not_tested",
)
AUDIT_POINT_ORIGINS = ("manual", "checklist", "analyzer")
AUDIT_POINT_STATUSES = ("open", "in_review", "converted_to_finding", "dismissed", "closed")
AUDIT_SEVERITIES = ("low", "medium", "high", "critical")


def _iso(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return None


class AuditArea(db.Model):
    __tablename__ = "audit_areas"
    __table_args__ = (
        db.Index("ix_audit_areas_company_active", "company_id", "active"),
        db.UniqueConstraint("company_id", "name", name="uq_audit_areas_company_name"),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    name = db.Column(db.String(180), nullable=False)
    description = db.Column(db.Text)
    manager_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    company = db.relationship("Company", foreign_keys=[company_id])
    manager_user = db.relationship("User", foreign_keys=[manager_user_id])

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "company_id": self.company_id,
            "name": self.name,
            "description": self.description,
            "manager_user_id": self.manager_user_id,
            "active": self.active,
            "created_at": _iso(self.created_at),
            "updated_at": _iso(self.updated_at),
        }


class AuditAuditor(db.Model):
    __tablename__ = "audit_auditors"
    __table_args__ = (
        db.UniqueConstraint("company_id", "user_id", name="uq_audit_auditors_company_user"),
        db.CheckConstraint("role IN ('auditor_admin','auditor','viewer_executivo')", name="ck_audit_auditors_role"),
        db.Index("ix_audit_auditors_company_active", "company_id", "active"),
        db.Index("ix_audit_auditors_company_role", "company_id", "role"),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey("employees.id", ondelete="SET NULL"))
    role = db.Column(db.String(40), nullable=False, default="auditor")
    active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    company = db.relationship("Company", foreign_keys=[company_id])
    user = db.relationship("User", foreign_keys=[user_id])
    employee = db.relationship("Employee", foreign_keys=[employee_id])

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "company_id": self.company_id,
            "user_id": self.user_id,
            "employee_id": self.employee_id,
            "role": self.role,
            "active": self.active,
            "user_name": getattr(self.user, "name", None),
            "employee_name": getattr(self.employee, "name", None),
            "created_at": _iso(self.created_at),
            "updated_at": _iso(self.updated_at),
        }


class AuditChecklist(db.Model):
    __tablename__ = "audit_checklists"
    __table_args__ = (
        db.CheckConstraint("checklist_type IN ('process','project','autonomous')", name="ck_audit_checklists_type"),
        db.Index("ix_audit_checklists_company_active", "company_id", "active"),
        db.Index("ix_audit_checklists_company_type", "company_id", "checklist_type"),
        db.Index("ix_audit_checklists_company_area", "company_id", "area_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    checklist_type = db.Column(db.String(30), nullable=False, default="autonomous")
    linked_process_id = db.Column(db.Integer, db.ForeignKey("processes.id", ondelete="SET NULL"))
    linked_project_id = db.Column(db.Integer, db.ForeignKey("projects.id", ondelete="SET NULL"))
    linked_routine_id = db.Column(db.Integer, db.ForeignKey("routines.id", ondelete="SET NULL"))
    area_id = db.Column(db.Integer, db.ForeignKey("audit_areas.id", ondelete="SET NULL"))
    owner_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    default_periodicity = db.Column(db.String(60))
    active = db.Column(db.Boolean, nullable=False, default=True)
    metadata_json = db.Column(JSONB, nullable=False, default=dict)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    company = db.relationship("Company", foreign_keys=[company_id])
    area = db.relationship("AuditArea", foreign_keys=[area_id])
    owner_user = db.relationship("User", foreign_keys=[owner_user_id])
    items = db.relationship(
        "AuditChecklistItem",
        back_populates="checklist",
        cascade="all, delete-orphan",
        order_by="AuditChecklistItem.sort_order.asc(), AuditChecklistItem.id.asc()",
    )

    def to_dict(self, include_items: bool = False) -> dict:
        payload = {
            "id": self.id,
            "company_id": self.company_id,
            "title": self.title,
            "description": self.description,
            "checklist_type": self.checklist_type,
            "linked_process_id": self.linked_process_id,
            "linked_project_id": self.linked_project_id,
            "linked_routine_id": self.linked_routine_id,
            "area_id": self.area_id,
            "area_name": getattr(self.area, "name", None),
            "owner_user_id": self.owner_user_id,
            "default_periodicity": self.default_periodicity,
            "active": self.active,
            "metadata": self.metadata_json or {},
            "created_at": _iso(self.created_at),
            "updated_at": _iso(self.updated_at),
        }
        if include_items:
            payload["items"] = [item.to_dict() for item in self.items]
        return payload


class AuditChecklistItem(db.Model):
    __tablename__ = "audit_checklist_items"
    __table_args__ = (
        db.Index("ix_audit_checklist_items_company_checklist", "company_id", "checklist_id"),
        db.Index("ix_audit_checklist_items_company_active", "company_id", "active"),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    checklist_id = db.Column(db.Integer, db.ForeignKey("audit_checklists.id", ondelete="CASCADE"), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description_for_report = db.Column(db.Text, nullable=False)
    expected_evidence = db.Column(db.Text)
    criterion = db.Column(db.Text)
    weight = db.Column(db.Numeric(8, 2))
    sort_order = db.Column(db.Integer, nullable=False, default=100)
    active = db.Column(db.Boolean, nullable=False, default=True)
    metadata_json = db.Column(JSONB, nullable=False, default=dict)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    checklist = db.relationship("AuditChecklist", back_populates="items", foreign_keys=[checklist_id])

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "company_id": self.company_id,
            "checklist_id": self.checklist_id,
            "title": self.title,
            "description_for_report": self.description_for_report,
            "expected_evidence": self.expected_evidence,
            "criterion": self.criterion,
            "weight": float(self.weight) if self.weight is not None else None,
            "sort_order": self.sort_order,
            "active": self.active,
            "metadata": self.metadata_json or {},
            "created_at": _iso(self.created_at),
            "updated_at": _iso(self.updated_at),
        }


class AuditExecution(db.Model):
    __tablename__ = "audit_executions"
    __table_args__ = (
        db.CheckConstraint(
            "status IN ('planned','in_progress','completed','cancelled')",
            name="ck_audit_executions_status",
        ),
        db.Index("ix_audit_executions_company_status", "company_id", "status"),
        db.Index("ix_audit_executions_company_checklist", "company_id", "checklist_id"),
        db.Index("ix_audit_executions_company_schedule", "company_id", "schedule_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    checklist_id = db.Column(db.Integer, db.ForeignKey("audit_checklists.id", ondelete="CASCADE"), nullable=False)
    schedule_id = db.Column(db.Integer, db.ForeignKey("audit_schedules.id", ondelete="SET NULL"))
    area_id = db.Column(db.Integer, db.ForeignKey("audit_areas.id", ondelete="SET NULL"))
    auditor_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    period_label = db.Column(db.String(120))
    planned_start_date = db.Column(db.Date)
    planned_end_date = db.Column(db.Date)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    status = db.Column(db.String(30), nullable=False, default="planned")
    metadata_json = db.Column(JSONB, nullable=False, default=dict)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    checklist = db.relationship("AuditChecklist", foreign_keys=[checklist_id])
    area = db.relationship("AuditArea", foreign_keys=[area_id])
    auditor_user = db.relationship("User", foreign_keys=[auditor_user_id])
    items = db.relationship(
        "AuditExecutionItem",
        back_populates="execution",
        cascade="all, delete-orphan",
        order_by="AuditExecutionItem.id.asc()",
    )

    def to_dict(self, include_items: bool = False) -> dict:
        payload = {
            "id": self.id,
            "company_id": self.company_id,
            "checklist_id": self.checklist_id,
            "checklist_title": getattr(self.checklist, "title", None),
            "schedule_id": self.schedule_id,
            "area_id": self.area_id,
            "area_name": getattr(self.area, "name", None),
            "auditor_user_id": self.auditor_user_id,
            "auditor_user_name": getattr(self.auditor_user, "name", None),
            "period_label": self.period_label,
            "planned_start_date": _iso(self.planned_start_date),
            "planned_end_date": _iso(self.planned_end_date),
            "started_at": _iso(self.started_at),
            "completed_at": _iso(self.completed_at),
            "status": self.status,
            "metadata": self.metadata_json or {},
            "created_at": _iso(self.created_at),
            "updated_at": _iso(self.updated_at),
        }
        if include_items:
            payload["items"] = [item.to_dict() for item in self.items]
        return payload


class AuditExecutionItem(db.Model):
    __tablename__ = "audit_execution_items"
    __table_args__ = (
        db.CheckConstraint(
            "status IN ('conforming','qualified_conforming','non_conforming','not_applicable','not_tested')",
            name="ck_audit_execution_items_status",
        ),
        db.UniqueConstraint("company_id", "execution_id", "checklist_item_id", name="uq_audit_execution_items_execution_item"),
        db.Index("ix_audit_execution_items_company_execution", "company_id", "execution_id"),
        db.Index("ix_audit_execution_items_company_status", "company_id", "status"),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    execution_id = db.Column(db.Integer, db.ForeignKey("audit_executions.id", ondelete="CASCADE"), nullable=False)
    checklist_item_id = db.Column(db.Integer, db.ForeignKey("audit_checklist_items.id", ondelete="CASCADE"), nullable=False)
    status = db.Column(db.String(40), nullable=False, default="not_tested")
    justification = db.Column(db.Text)
    comments = db.Column(db.Text)
    audit_point_id = db.Column(db.Integer, db.ForeignKey("audit_points.id", ondelete="SET NULL"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    execution = db.relationship("AuditExecution", back_populates="items", foreign_keys=[execution_id])
    checklist_item = db.relationship("AuditChecklistItem", foreign_keys=[checklist_item_id])
    audit_point = db.relationship("AuditPoint", foreign_keys=[audit_point_id], post_update=True)

    def to_dict(self) -> dict:
        item = self.checklist_item
        return {
            "id": self.id,
            "company_id": self.company_id,
            "execution_id": self.execution_id,
            "checklist_item_id": self.checklist_item_id,
            "checklist_item_title": getattr(item, "title", None),
            "description_for_report": getattr(item, "description_for_report", None),
            "expected_evidence": getattr(item, "expected_evidence", None),
            "criterion": getattr(item, "criterion", None),
            "status": self.status,
            "justification": self.justification,
            "comments": self.comments,
            "audit_point_id": self.audit_point_id,
            "created_at": _iso(self.created_at),
            "updated_at": _iso(self.updated_at),
        }


class AuditPoint(db.Model):
    __tablename__ = "audit_points"
    __table_args__ = (
        db.CheckConstraint("origin_type IN ('manual','checklist','analyzer')", name="ck_audit_points_origin_type"),
        db.CheckConstraint("severity IN ('low','medium','high','critical')", name="ck_audit_points_severity"),
        db.CheckConstraint(
            "status IN ('open','in_review','converted_to_finding','dismissed','closed')",
            name="ck_audit_points_status",
        ),
        db.Index("ix_audit_points_company_status", "company_id", "status"),
        db.Index("ix_audit_points_company_severity", "company_id", "severity"),
        db.Index("ix_audit_points_company_due_date", "company_id", "due_date"),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    origin_type = db.Column(db.String(30), nullable=False, default="manual")
    source_module = db.Column(db.String(60), nullable=False, default="audit")
    subject_type = db.Column(db.String(80))
    subject_id = db.Column(db.Integer)
    severity = db.Column(db.String(30), nullable=False, default="medium")
    status = db.Column(db.String(40), nullable=False, default="open")
    assigned_to_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    detected_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    due_date = db.Column(db.Date)
    metadata_json = db.Column(JSONB, nullable=False, default=dict)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    assigned_to_user = db.relationship("User", foreign_keys=[assigned_to_user_id])

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "company_id": self.company_id,
            "title": self.title,
            "description": self.description,
            "origin_type": self.origin_type,
            "source_module": self.source_module,
            "subject_type": self.subject_type,
            "subject_id": self.subject_id,
            "severity": self.severity,
            "status": self.status,
            "assigned_to_user_id": self.assigned_to_user_id,
            "assigned_to_user_name": getattr(self.assigned_to_user, "name", None),
            "detected_at": _iso(self.detected_at),
            "due_date": _iso(self.due_date),
            "metadata": self.metadata_json or {},
            "created_at": _iso(self.created_at),
            "updated_at": _iso(self.updated_at),
        }


class AuditSchedule(db.Model):
    __tablename__ = "audit_schedules"
    __table_args__ = (
        db.CheckConstraint("status IN ('active','paused','completed','cancelled')", name="ck_audit_schedules_status"),
        db.Index("ix_audit_schedules_company_status", "company_id", "status"),
        db.Index("ix_audit_schedules_company_checklist", "company_id", "checklist_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    process_id = db.Column(db.Integer, db.ForeignKey("processes.id", ondelete="SET NULL"))
    routine_id = db.Column(db.Integer, db.ForeignKey("routines.id", ondelete="SET NULL"))
    checklist_id = db.Column(db.Integer, db.ForeignKey("audit_checklists.id", ondelete="SET NULL"))
    area_id = db.Column(db.Integer, db.ForeignKey("audit_areas.id", ondelete="SET NULL"))
    auditor_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    planned_start_date = db.Column(db.Date)
    planned_end_date = db.Column(db.Date)
    recurrence_rule = db.Column(db.String(255))
    status = db.Column(db.String(30), nullable=False, default="active")
    metadata_json = db.Column(JSONB, nullable=False, default=dict)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "company_id": self.company_id,
            "title": self.title,
            "process_id": self.process_id,
            "routine_id": self.routine_id,
            "checklist_id": self.checklist_id,
            "area_id": self.area_id,
            "auditor_user_id": self.auditor_user_id,
            "planned_start_date": _iso(self.planned_start_date),
            "planned_end_date": _iso(self.planned_end_date),
            "recurrence_rule": self.recurrence_rule,
            "status": self.status,
            "metadata": self.metadata_json or {},
            "created_at": _iso(self.created_at),
            "updated_at": _iso(self.updated_at),
        }
