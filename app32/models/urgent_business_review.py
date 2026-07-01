from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from . import db


URGENT_NEED_STATUS_VALUES = (
    "inbox",
    "triage",
    "in_review",
    "decided",
    "in_execution",
    "closed",
    "cancelled",
)

URGENT_NEED_LEVEL_VALUES = ("low", "medium", "high", "critical")

URGENT_NEED_CRITICALITY_VALUES = (
    "operational",
    "managerial",
    "strategic",
    "legal_regulatory",
    "financial",
    "reputational",
)

BUSINESS_REVIEW_TYPE_VALUES = (
    "urgent_need",
    "project_investment",
    "process_correction",
    "risk_acceptance",
    "strategic_decision",
    "financial_impact",
)

BUSINESS_REVIEW_STATUS_VALUES = (
    "draft",
    "in_analysis",
    "pending_decision",
    "approved",
    "risk_accepted",
    "rejected",
    "closed",
)

STRUCTURAL_LEARNING_TYPE_VALUES = (
    "process_change",
    "routine_change",
    "indicator_change",
    "control_change",
    "policy_change",
    "project_creation",
    "task_creation",
    "risk_acceptance",
    "no_structural_action",
)

STRUCTURAL_LEARNING_ACTION_VALUES = (
    "recommended",
    "approved",
    "rejected",
    "risk_accepted",
    "converted_to_project",
    "converted_to_task",
    "closed_no_action",
)


def _iso(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return None


def _decimal(value):
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    return value


class UrgentNeedOverlay(db.Model):
    """Overlay consultivo de Necessidade Urgente sobre objetos canônicos.

    Não substitui projeto, tarefa, processo, indicador ou reunião. A tabela
    registra apenas a leitura Versus de urgência, impacto, risco e decisão.
    """

    __tablename__ = "urgent_need_overlays"
    __table_args__ = (
        db.CheckConstraint(
            f"status IN {URGENT_NEED_STATUS_VALUES}",
            name="ck_urgent_need_overlays_status",
        ),
        db.CheckConstraint(
            f"urgency_level IN {URGENT_NEED_LEVEL_VALUES}",
            name="ck_urgent_need_overlays_urgency_level",
        ),
        db.CheckConstraint(
            f"criticality_level IN {URGENT_NEED_CRITICALITY_VALUES}",
            name="ck_urgent_need_overlays_criticality_level",
        ),
        db.CheckConstraint(
            """
            project_id IS NOT NULL OR project_task_id IS NOT NULL OR process_id IS NOT NULL OR
            process_instance_id IS NOT NULL OR routine_id IS NOT NULL OR indicator_id IS NOT NULL OR
            meeting_id IS NOT NULL OR occurrence_id IS NOT NULL
            """,
            name="ck_urgent_need_overlays_has_canonical_link",
        ),
        db.Index("ix_urgent_need_overlays_company_status", "company_id", "status"),
        db.Index("ix_urgent_need_overlays_company_urgency", "company_id", "urgency_level"),
        db.Index("ix_urgent_need_overlays_company_project", "company_id", "project_id"),
        db.Index("ix_urgent_need_overlays_company_task", "company_id", "project_task_id"),
        db.Index("ix_urgent_need_overlays_company_process", "company_id", "process_id"),
        db.Index("ix_urgent_need_overlays_company_indicator", "company_id", "indicator_id"),
        {"extend_existing": True},
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(30), nullable=False, default="inbox")
    urgency_level = db.Column(db.String(20), nullable=False, default="medium")
    criticality_level = db.Column(db.String(40), nullable=False, default="operational")
    origin_channel = db.Column(db.String(60))
    origin_summary = db.Column(db.Text)

    project_id = db.Column(db.Integer, db.ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    project_task_id = db.Column(db.Integer, db.ForeignKey("project_tasks.id", ondelete="SET NULL"), nullable=True)
    process_id = db.Column(db.Integer, db.ForeignKey("processes.id", ondelete="SET NULL"), nullable=True)
    process_instance_id = db.Column(db.Integer, db.ForeignKey("process_instances.id", ondelete="SET NULL"), nullable=True)
    routine_id = db.Column(db.Integer, db.ForeignKey("routines.id", ondelete="SET NULL"), nullable=True)
    indicator_id = db.Column(db.Integer, db.ForeignKey("indicators.id", ondelete="SET NULL"), nullable=True)
    meeting_id = db.Column(db.Integer, db.ForeignKey("meetings.id", ondelete="SET NULL"), nullable=True)
    occurrence_id = db.Column(db.Integer, db.ForeignKey("occurrences.id", ondelete="SET NULL"), nullable=True)
    financial_ref_id = db.Column(db.Integer, nullable=True)

    source_type = db.Column(db.String(80))
    source_ref_id = db.Column(db.String(120))
    source_payload_json = db.Column(db.JSON, default=dict)

    business_impact_summary = db.Column(db.Text)
    operational_impact_summary = db.Column(db.Text)
    risk_summary = db.Column(db.Text)
    decision_status = db.Column(db.String(40), nullable=False, default="pending")
    decision_summary = db.Column(db.Text)

    responsible_employee_id = db.Column(db.Integer, db.ForeignKey("employees.id", ondelete="SET NULL"), nullable=True)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    closed_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    closed_at = db.Column(db.DateTime)

    company = db.relationship("Company", foreign_keys=[company_id])
    project = db.relationship("Project", foreign_keys=[project_id])
    project_task = db.relationship("ProjectTask", foreign_keys=[project_task_id])
    process = db.relationship("Process", foreign_keys=[process_id])
    process_instance = db.relationship("ProcessInstance", foreign_keys=[process_instance_id])
    routine = db.relationship("Routine", foreign_keys=[routine_id])
    indicator = db.relationship("Indicator", foreign_keys=[indicator_id])
    meeting = db.relationship("Meeting", foreign_keys=[meeting_id])
    occurrence = db.relationship("Occurrence", foreign_keys=[occurrence_id])
    responsible_employee = db.relationship("Employee", foreign_keys=[responsible_employee_id])

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "company_id": self.company_id,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "urgency_level": self.urgency_level,
            "criticality_level": self.criticality_level,
            "origin_channel": self.origin_channel,
            "origin_summary": self.origin_summary,
            "project_id": self.project_id,
            "project_task_id": self.project_task_id,
            "process_id": self.process_id,
            "process_instance_id": self.process_instance_id,
            "routine_id": self.routine_id,
            "indicator_id": self.indicator_id,
            "meeting_id": self.meeting_id,
            "occurrence_id": self.occurrence_id,
            "financial_ref_id": self.financial_ref_id,
            "source_type": self.source_type,
            "source_ref_id": self.source_ref_id,
            "source_payload": self.source_payload_json or {},
            "business_impact_summary": self.business_impact_summary,
            "operational_impact_summary": self.operational_impact_summary,
            "risk_summary": self.risk_summary,
            "decision_status": self.decision_status,
            "decision_summary": self.decision_summary,
            "responsible_employee_id": self.responsible_employee_id,
            "created_by_user_id": self.created_by_user_id,
            "updated_by_user_id": self.updated_by_user_id,
            "closed_by_user_id": self.closed_by_user_id,
            "created_at": _iso(self.created_at),
            "updated_at": _iso(self.updated_at),
            "closed_at": _iso(self.closed_at),
        }


class BusinessReviewRecord(db.Model):
    """Registro consultivo de Business Review da metodologia Versus."""

    __tablename__ = "business_review_records"
    __table_args__ = (
        db.CheckConstraint(
            f"review_type IN {BUSINESS_REVIEW_TYPE_VALUES}",
            name="ck_business_review_records_review_type",
        ),
        db.CheckConstraint(
            f"status IN {BUSINESS_REVIEW_STATUS_VALUES}",
            name="ck_business_review_records_status",
        ),
        db.CheckConstraint(
            "risk_acceptance_decision IS DISTINCT FROM TRUE OR btrim(risk_acceptance_reason) <> ''",
            name="ck_business_review_records_risk_reason",
        ),
        db.Index("ix_business_review_records_company_status", "company_id", "status"),
        db.Index("ix_business_review_records_company_type", "company_id", "review_type"),
        db.Index("ix_business_review_records_company_urgent_need", "company_id", "urgent_need_id"),
        db.Index("ix_business_review_records_company_project", "company_id", "project_id"),
        db.Index("ix_business_review_records_company_process", "company_id", "process_id"),
        {"extend_existing": True},
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    review_type = db.Column(db.String(40), nullable=False, default="urgent_need")
    status = db.Column(db.String(30), nullable=False, default="draft")

    urgent_need_id = db.Column(db.Integer, db.ForeignKey("urgent_need_overlays.id", ondelete="SET NULL"), nullable=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    project_task_id = db.Column(db.Integer, db.ForeignKey("project_tasks.id", ondelete="SET NULL"), nullable=True)
    process_id = db.Column(db.Integer, db.ForeignKey("processes.id", ondelete="SET NULL"), nullable=True)
    indicator_id = db.Column(db.Integer, db.ForeignKey("indicators.id", ondelete="SET NULL"), nullable=True)
    meeting_id = db.Column(db.Integer, db.ForeignKey("meetings.id", ondelete="SET NULL"), nullable=True)

    cost_to_act = db.Column(db.Numeric(14, 2))
    cost_to_not_act = db.Column(db.Numeric(14, 2))
    required_investment = db.Column(db.Numeric(14, 2))
    expected_gain = db.Column(db.Numeric(14, 2))
    expected_return = db.Column(db.Numeric(14, 2))
    risk_level = db.Column(db.String(20), nullable=False, default="medium")
    risk_acceptance_decision = db.Column(db.Boolean, nullable=False, default=False)
    risk_acceptance_reason = db.Column(db.Text)

    decision_summary = db.Column(db.Text)
    structural_learning_summary = db.Column(db.Text)
    next_action = db.Column(db.Text)

    responsible_employee_id = db.Column(db.Integer, db.ForeignKey("employees.id", ondelete="SET NULL"), nullable=True)
    reviewed_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    reviewed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    closed_at = db.Column(db.DateTime)

    company = db.relationship("Company", foreign_keys=[company_id])
    urgent_need = db.relationship("UrgentNeedOverlay", foreign_keys=[urgent_need_id], backref=db.backref("business_reviews", lazy="dynamic"))
    project = db.relationship("Project", foreign_keys=[project_id])
    project_task = db.relationship("ProjectTask", foreign_keys=[project_task_id])
    process = db.relationship("Process", foreign_keys=[process_id])
    indicator = db.relationship("Indicator", foreign_keys=[indicator_id])
    meeting = db.relationship("Meeting", foreign_keys=[meeting_id])
    responsible_employee = db.relationship("Employee", foreign_keys=[responsible_employee_id])

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "company_id": self.company_id,
            "title": self.title,
            "review_type": self.review_type,
            "status": self.status,
            "urgent_need_id": self.urgent_need_id,
            "project_id": self.project_id,
            "project_task_id": self.project_task_id,
            "process_id": self.process_id,
            "indicator_id": self.indicator_id,
            "meeting_id": self.meeting_id,
            "cost_to_act": _decimal(self.cost_to_act),
            "cost_to_not_act": _decimal(self.cost_to_not_act),
            "required_investment": _decimal(self.required_investment),
            "expected_gain": _decimal(self.expected_gain),
            "expected_return": _decimal(self.expected_return),
            "risk_level": self.risk_level,
            "risk_acceptance_decision": bool(self.risk_acceptance_decision),
            "risk_acceptance_reason": self.risk_acceptance_reason,
            "decision_summary": self.decision_summary,
            "structural_learning_summary": self.structural_learning_summary,
            "next_action": self.next_action,
            "responsible_employee_id": self.responsible_employee_id,
            "reviewed_by_user_id": self.reviewed_by_user_id,
            "created_by_user_id": self.created_by_user_id,
            "updated_by_user_id": self.updated_by_user_id,
            "reviewed_at": _iso(self.reviewed_at),
            "created_at": _iso(self.created_at),
            "updated_at": _iso(self.updated_at),
            "closed_at": _iso(self.closed_at),
        }


class StructuralLearningLink(db.Model):
    """Aprendizado estrutural derivado de uma urgência ou Business Review."""

    __tablename__ = "structural_learning_links"
    __table_args__ = (
        db.CheckConstraint(
            f"learning_type IN {STRUCTURAL_LEARNING_TYPE_VALUES}",
            name="ck_structural_learning_links_learning_type",
        ),
        db.CheckConstraint(
            f"action_decision IN {STRUCTURAL_LEARNING_ACTION_VALUES}",
            name="ck_structural_learning_links_action_decision",
        ),
        db.CheckConstraint(
            "action_decision != 'risk_accepted' OR btrim(accepted_risk_reason) <> ''",
            name="ck_structural_learning_links_risk_reason",
        ),
        db.Index("ix_structural_learning_links_company_review", "company_id", "business_review_id"),
        db.Index("ix_structural_learning_links_company_urgent_need", "company_id", "urgent_need_id"),
        db.Index("ix_structural_learning_links_company_process", "company_id", "target_process_id"),
        {"extend_existing": True},
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    business_review_id = db.Column(db.Integer, db.ForeignKey("business_review_records.id", ondelete="CASCADE"), nullable=False)
    urgent_need_id = db.Column(db.Integer, db.ForeignKey("urgent_need_overlays.id", ondelete="SET NULL"), nullable=True)

    target_project_id = db.Column(db.Integer, db.ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    target_project_task_id = db.Column(db.Integer, db.ForeignKey("project_tasks.id", ondelete="SET NULL"), nullable=True)
    target_process_id = db.Column(db.Integer, db.ForeignKey("processes.id", ondelete="SET NULL"), nullable=True)
    target_routine_id = db.Column(db.Integer, db.ForeignKey("routines.id", ondelete="SET NULL"), nullable=True)
    target_indicator_id = db.Column(db.Integer, db.ForeignKey("indicators.id", ondelete="SET NULL"), nullable=True)
    target_meeting_id = db.Column(db.Integer, db.ForeignKey("meetings.id", ondelete="SET NULL"), nullable=True)

    learning_type = db.Column(db.String(40), nullable=False)
    action_decision = db.Column(db.String(40), nullable=False, default="recommended")
    accepted_risk_reason = db.Column(db.Text)
    recommended_change = db.Column(db.Text)

    created_project_id = db.Column(db.Integer, db.ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    created_task_id = db.Column(db.Integer, db.ForeignKey("project_tasks.id", ondelete="SET NULL"), nullable=True)

    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    company = db.relationship("Company", foreign_keys=[company_id])
    business_review = db.relationship("BusinessReviewRecord", foreign_keys=[business_review_id], backref=db.backref("structural_learning_links", lazy="dynamic"))
    urgent_need = db.relationship("UrgentNeedOverlay", foreign_keys=[urgent_need_id])
    target_project = db.relationship("Project", foreign_keys=[target_project_id])
    target_project_task = db.relationship("ProjectTask", foreign_keys=[target_project_task_id])
    target_process = db.relationship("Process", foreign_keys=[target_process_id])
    target_routine = db.relationship("Routine", foreign_keys=[target_routine_id])
    target_indicator = db.relationship("Indicator", foreign_keys=[target_indicator_id])
    target_meeting = db.relationship("Meeting", foreign_keys=[target_meeting_id])
    created_project = db.relationship("Project", foreign_keys=[created_project_id])
    created_task = db.relationship("ProjectTask", foreign_keys=[created_task_id])

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "company_id": self.company_id,
            "business_review_id": self.business_review_id,
            "urgent_need_id": self.urgent_need_id,
            "target_project_id": self.target_project_id,
            "target_project_task_id": self.target_project_task_id,
            "target_process_id": self.target_process_id,
            "target_routine_id": self.target_routine_id,
            "target_indicator_id": self.target_indicator_id,
            "target_meeting_id": self.target_meeting_id,
            "learning_type": self.learning_type,
            "action_decision": self.action_decision,
            "accepted_risk_reason": self.accepted_risk_reason,
            "recommended_change": self.recommended_change,
            "created_project_id": self.created_project_id,
            "created_task_id": self.created_task_id,
            "created_by_user_id": self.created_by_user_id,
            "updated_by_user_id": self.updated_by_user_id,
            "created_at": _iso(self.created_at),
            "updated_at": _iso(self.updated_at),
        }


__all__ = [
    "URGENT_NEED_STATUS_VALUES",
    "URGENT_NEED_LEVEL_VALUES",
    "URGENT_NEED_CRITICALITY_VALUES",
    "BUSINESS_REVIEW_TYPE_VALUES",
    "BUSINESS_REVIEW_STATUS_VALUES",
    "STRUCTURAL_LEARNING_TYPE_VALUES",
    "STRUCTURAL_LEARNING_ACTION_VALUES",
    "UrgentNeedOverlay",
    "BusinessReviewRecord",
    "StructuralLearningLink",
]
