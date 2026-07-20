from __future__ import annotations

from datetime import date, datetime

from . import db


CONSULTIVE_FRONT_KEY_VALUES = (
    "identity",
    "processes",
    "growth_plan",
    "strategic_management",
)

ASSISTED_ANALYSIS_TYPE_VALUES = (
    "methodological",
    "technical_test",
)

ASSISTED_ANALYSIS_STATUS_VALUES = (
    "received",
    "under_review",
    "validated",
    "rejected",
    "conversion_requested",
    "converted",
    "archived",
)

ASSISTED_ANALYSIS_VALIDATION_SQUAD_VALUES = (
    "client",
    "versus",
    "engineering",
)

ASSISTED_ANALYSIS_VALIDATION_STATUS_VALUES = (
    "pending",
    "validated",
    "rejected",
    "needs_adjustment",
)

ASSISTED_ANALYSIS_DECISION_VALUES = (
    "accept",
    "adjust",
    "reject",
    "hold",
)

ASSISTED_ANALYSIS_CONVERSION_TARGET_VALUES = (
    "none",
    "project",
    "process",
    "indicator",
    "routine",
    "business_review",
    "urgent_need",
    "structural_learning",
)


def _iso(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return None


class AssistedAnalysis(db.Model):
    """Resultado trazido pela IA/CLI via MCP para uma frente consultiva.

    A tabela registra a análise recebida, sem executar IA dentro do APP32 e sem
    converter automaticamente recomendação em objeto operacional.
    """

    __tablename__ = "consultive_assisted_analyses"
    __table_args__ = (
        db.CheckConstraint(
            f"front_key IN {CONSULTIVE_FRONT_KEY_VALUES}",
            name="ck_consultive_assisted_analyses_front_key",
        ),
        db.CheckConstraint(
            f"analysis_type IN {ASSISTED_ANALYSIS_TYPE_VALUES}",
            name="ck_consultive_assisted_analyses_analysis_type",
        ),
        db.CheckConstraint(
            f"status IN {ASSISTED_ANALYSIS_STATUS_VALUES}",
            name="ck_consultive_assisted_analyses_status",
        ),
        db.Index("ix_consultive_assisted_analyses_company_front", "company_id", "front_key"),
        db.Index("ix_consultive_assisted_analyses_company_status", "company_id", "status"),
        {"extend_existing": True},
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    front_key = db.Column(db.String(40), nullable=False)
    status = db.Column(db.String(30), nullable=False, default="received")
    analysis_type = db.Column(db.String(30), nullable=False, default="technical_test")
    journey_eligible = db.Column(db.Boolean, nullable=False, default=False)
    eligibility_reasons_json = db.Column(db.JSON, default=list)

    ai_origin = db.Column(db.String(120))
    responsible = db.Column(db.String(160))
    diagnosis = db.Column(db.Text, nullable=False)
    benchmarks = db.Column(db.Text)
    risks = db.Column(db.Text)
    recommendations = db.Column(db.Text)
    source_payload_json = db.Column(db.JSON, default=dict)

    protocol_id = db.Column(db.Integer, db.ForeignKey("consultive_protocols.id", ondelete="SET NULL"), nullable=True)
    protocol_version = db.Column(db.String(40))
    protocol_source = db.Column(db.String(40))
    protocol_title = db.Column(db.String(255))
    protocol_snapshot_json = db.Column(db.JSON, default=dict)

    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    company = db.relationship("Company", foreign_keys=[company_id])
    protocol = db.relationship("ConsultiveProtocol", foreign_keys=[protocol_id])

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "company_id": self.company_id,
            "front_key": self.front_key,
            "status": self.status,
            "analysis_type": self.analysis_type,
            "journey_eligible": bool(self.journey_eligible),
            "eligibility_reasons": list(self.eligibility_reasons_json or []),
            "ai_origin": self.ai_origin,
            "responsible": self.responsible,
            "diagnosis": self.diagnosis,
            "benchmarks": self.benchmarks,
            "risks": self.risks,
            "recommendations": self.recommendations,
            "source_payload": self.source_payload_json or {},
            "protocol_id": self.protocol_id,
            "protocol_version": self.protocol_version,
            "protocol_source": self.protocol_source,
            "protocol_title": self.protocol_title,
            "protocol_snapshot": self.protocol_snapshot_json or {},
            "created_by_user_id": self.created_by_user_id,
            "updated_by_user_id": self.updated_by_user_id,
            "created_at": _iso(self.created_at),
            "updated_at": _iso(self.updated_at),
        }


class AssistedAnalysisValidation(db.Model):
    """Validação de squad sobre análise assistida recebida."""

    __tablename__ = "consultive_assisted_analysis_validations"
    __table_args__ = (
        db.CheckConstraint(
            f"squad IN {ASSISTED_ANALYSIS_VALIDATION_SQUAD_VALUES}",
            name="ck_consultive_assisted_analysis_validations_squad",
        ),
        db.CheckConstraint(
            f"status IN {ASSISTED_ANALYSIS_VALIDATION_STATUS_VALUES}",
            name="ck_consultive_assisted_analysis_validations_status",
        ),
        db.UniqueConstraint("analysis_id", "squad", name="uq_consultive_assisted_analysis_validations_analysis_squad"),
        db.Index("ix_consultive_assisted_analysis_validations_company_analysis", "company_id", "analysis_id"),
        {"extend_existing": True},
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    analysis_id = db.Column(db.Integer, db.ForeignKey("consultive_assisted_analyses.id", ondelete="CASCADE"), nullable=False)
    squad = db.Column(db.String(30), nullable=False)
    status = db.Column(db.String(30), nullable=False, default="pending")
    notes = db.Column(db.Text)
    validated_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    company = db.relationship("Company", foreign_keys=[company_id])
    analysis = db.relationship("AssistedAnalysis", foreign_keys=[analysis_id], backref=db.backref("validations", lazy="dynamic"))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "company_id": self.company_id,
            "analysis_id": self.analysis_id,
            "squad": self.squad,
            "status": self.status,
            "notes": self.notes,
            "validated_by_user_id": self.validated_by_user_id,
            "created_at": _iso(self.created_at),
            "updated_at": _iso(self.updated_at),
        }


class AssistedAnalysisDecision(db.Model):
    """Decisão humana do consultor sobre uma análise assistida."""

    __tablename__ = "consultive_assisted_analysis_decisions"
    __table_args__ = (
        db.CheckConstraint(
            f"decision IN {ASSISTED_ANALYSIS_DECISION_VALUES}",
            name="ck_consultive_assisted_analysis_decisions_decision",
        ),
        db.CheckConstraint(
            f"conversion_target IN {ASSISTED_ANALYSIS_CONVERSION_TARGET_VALUES}",
            name="ck_consultive_assisted_analysis_decisions_conversion_target",
        ),
        db.Index("ix_consultive_assisted_analysis_decisions_company_analysis", "company_id", "analysis_id"),
        {"extend_existing": True},
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    analysis_id = db.Column(db.Integer, db.ForeignKey("consultive_assisted_analyses.id", ondelete="CASCADE"), nullable=False)
    decision = db.Column(db.String(30), nullable=False)
    conversion_target = db.Column(db.String(40), nullable=False, default="none")
    decision_reason = db.Column(db.Text, nullable=False)
    next_action = db.Column(db.Text)
    governance_notes = db.Column(db.Text)
    decided_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    company = db.relationship("Company", foreign_keys=[company_id])
    analysis = db.relationship("AssistedAnalysis", foreign_keys=[analysis_id], backref=db.backref("decisions", lazy="dynamic"))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "company_id": self.company_id,
            "analysis_id": self.analysis_id,
            "decision": self.decision,
            "conversion_target": self.conversion_target,
            "decision_reason": self.decision_reason,
            "next_action": self.next_action,
            "governance_notes": self.governance_notes,
            "decided_by_user_id": self.decided_by_user_id,
            "created_at": _iso(self.created_at),
            "updated_at": _iso(self.updated_at),
        }


__all__ = [
    "CONSULTIVE_FRONT_KEY_VALUES",
    "ASSISTED_ANALYSIS_TYPE_VALUES",
    "ASSISTED_ANALYSIS_STATUS_VALUES",
    "ASSISTED_ANALYSIS_VALIDATION_SQUAD_VALUES",
    "ASSISTED_ANALYSIS_VALIDATION_STATUS_VALUES",
    "ASSISTED_ANALYSIS_DECISION_VALUES",
    "ASSISTED_ANALYSIS_CONVERSION_TARGET_VALUES",
    "AssistedAnalysis",
    "AssistedAnalysisValidation",
    "AssistedAnalysisDecision",
]
