from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy.dialects.postgresql import JSONB

from . import db


STRATEGY_ALIGNMENT_LINK_TYPES = (
    "strategic_objective",
    "strategic_pillar",
    "value_proposition",
    "differential",
    "essential_competence",
    "policy",
)

STRATEGY_ALIGNMENT_TARGET_REF_TYPES = (
    "identity_json",
    "okr_global",
    "okr_area",
    "plan_driver",
    "indicator",
    "policy",
    "custom",
)

PROCESS_STRATEGIC_CRITICALITY_VALUES = ("alta", "media", "baixa")
PROCESS_MATURITY_LEVEL_VALUES = (
    "nao_definido",
    "inicial",
    "gerenciado",
    "padronizado",
    "mensurado",
    "otimizado",
)
INDICATOR_LINE_OF_SIGHT_RELATIONSHIP_TYPES = (
    "contributes_to",
    "drives",
    "rolls_up_to",
    "correlates_with",
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


class OrganizationalIdentity(db.Model):
    """Identidade organizacional estruturada para análises estratégicas."""

    __tablename__ = "organizational_identities"
    __table_args__ = (
        db.UniqueConstraint("company_id", name="uq_organizational_identities_company"),
        db.Index("ix_organizational_identities_company_id", "company_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)

    mission = db.Column(db.Text)
    vision = db.Column(db.Text)
    vision_horizon_year = db.Column(db.Integer)
    purpose = db.Column(db.Text)

    values_json = db.Column(JSONB, nullable=False, default=list)
    value_propositions_json = db.Column(JSONB, nullable=False, default=list)
    differentials_json = db.Column(JSONB, nullable=False, default=list)
    pillars_json = db.Column(JSONB, nullable=False, default=list)
    strategic_objectives_json = db.Column(JSONB, nullable=False, default=list)
    essential_competencies_json = db.Column(JSONB, nullable=False, default=list)
    segments_icp_json = db.Column(JSONB, nullable=False, default=list)
    policies_json = db.Column(JSONB, nullable=False, default=list)
    stakeholders_json = db.Column(JSONB, nullable=False, default=list)
    swot_json = db.Column(JSONB, nullable=False, default=dict)
    corporate_indicators_json = db.Column(JSONB, nullable=False, default=list)

    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    updated_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    company = db.relationship("Company", foreign_keys=[company_id])

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "company_id": self.company_id,
            "mission": self.mission,
            "vision": self.vision,
            "vision_horizon_year": self.vision_horizon_year,
            "purpose": self.purpose,
            "values": self.values_json or [],
            "value_propositions": self.value_propositions_json or [],
            "differentials": self.differentials_json or [],
            "pillars": self.pillars_json or [],
            "strategic_objectives": self.strategic_objectives_json or [],
            "essential_competencies": self.essential_competencies_json or [],
            "segments_icp": self.segments_icp_json or [],
            "policies": self.policies_json or [],
            "stakeholders": self.stakeholders_json or [],
            "swot": self.swot_json or {},
            "corporate_indicators": self.corporate_indicators_json or [],
            "created_by_user_id": self.created_by_user_id,
            "updated_by_user_id": self.updated_by_user_id,
            "created_at": _iso(self.created_at),
            "updated_at": _iso(self.updated_at),
            "structured": True,
        }


class ProcessStrategyProfile(db.Model):
    """Complemento estratégico estruturado de um processo."""

    __tablename__ = "process_strategy_profiles"
    __table_args__ = (
        db.UniqueConstraint("company_id", "process_id", name="uq_process_strategy_profiles_company_process"),
        db.ForeignKeyConstraint(
            ["company_id", "process_id"],
            ["processes.company_id", "processes.id"],
            ondelete="CASCADE",
            name="fk_process_strategy_profiles_company_process",
        ),
        db.CheckConstraint(
            f"strategic_criticality IS NULL OR strategic_criticality IN {PROCESS_STRATEGIC_CRITICALITY_VALUES}",
            name="ck_process_strategy_profiles_criticality",
        ),
        db.CheckConstraint(
            f"maturity_level IS NULL OR maturity_level IN {PROCESS_MATURITY_LEVEL_VALUES}",
            name="ck_process_strategy_profiles_maturity",
        ),
        db.Index("ix_process_strategy_profiles_company_process", "company_id", "process_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    process_id = db.Column(db.Integer, nullable=False, index=True)

    objective = db.Column(db.Text)
    owner = db.Column(db.String(255))
    owner_employee_id = db.Column(db.Integer, db.ForeignKey("employees.id", ondelete="SET NULL"))
    customer_type = db.Column(db.String(40))
    customer_description = db.Column(db.Text)
    strategic_criticality = db.Column(db.String(20))
    maturity_level = db.Column(db.String(40))
    regulatory_exposure = db.Column(db.Text)

    indicators_json = db.Column(JSONB, nullable=False, default=list)
    sipoc_json = db.Column(JSONB, nullable=False, default=dict)
    cost_resources_volume_json = db.Column(JSONB, nullable=False, default=dict)
    applicable_policies_json = db.Column(JSONB, nullable=False, default=list)
    risks_json = db.Column(JSONB, nullable=False, default=list)

    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    updated_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    company = db.relationship("Company", foreign_keys=[company_id])
    process = db.relationship("Process", foreign_keys=[process_id])

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "company_id": self.company_id,
            "process_id": self.process_id,
            "objective": self.objective,
            "owner": self.owner,
            "owner_employee_id": self.owner_employee_id,
            "customer_type": self.customer_type,
            "customer_description": self.customer_description,
            "strategic_criticality": self.strategic_criticality,
            "maturity_level": self.maturity_level,
            "regulatory_exposure": self.regulatory_exposure,
            "indicators": self.indicators_json or [],
            "sipoc": self.sipoc_json or {},
            "cost_resources_volume": self.cost_resources_volume_json or {},
            "applicable_policies": self.applicable_policies_json or [],
            "risks": self.risks_json or [],
            "created_by_user_id": self.created_by_user_id,
            "updated_by_user_id": self.updated_by_user_id,
            "created_at": _iso(self.created_at),
            "updated_at": _iso(self.updated_at),
        }


class ProcessStrategicAlignmentLink(db.Model):
    """Rastreabilidade Processo -> objeto estratégico/política/competência."""

    __tablename__ = "process_strategic_alignment_links"
    __table_args__ = (
        db.ForeignKeyConstraint(
            ["company_id", "process_id"],
            ["processes.company_id", "processes.id"],
            ondelete="CASCADE",
            name="fk_process_alignment_links_company_process",
        ),
        db.CheckConstraint(
            f"link_type IN {STRATEGY_ALIGNMENT_LINK_TYPES}",
            name="ck_process_alignment_links_type",
        ),
        db.CheckConstraint(
            f"target_ref_type IS NULL OR target_ref_type IN {STRATEGY_ALIGNMENT_TARGET_REF_TYPES}",
            name="ck_process_alignment_links_target_ref_type",
        ),
        db.Index("ix_process_alignment_links_company_process", "company_id", "process_id"),
        db.Index("ix_process_alignment_links_company_type", "company_id", "link_type"),
        db.Index("ix_process_alignment_links_target", "company_id", "target_ref_type", "target_ref_id", "target_key"),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    process_id = db.Column(db.Integer, nullable=False, index=True)
    link_type = db.Column(db.String(60), nullable=False)
    target_ref_type = db.Column(db.String(60))
    target_ref_id = db.Column(db.Integer)
    target_key = db.Column(db.String(180))
    target_payload_json = db.Column(JSONB, nullable=False, default=dict)
    contribution_type = db.Column(db.String(80))
    contribution_weight = db.Column(db.Numeric(7, 4))
    notes = db.Column(db.Text)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    updated_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    company = db.relationship("Company", foreign_keys=[company_id])
    process = db.relationship("Process", foreign_keys=[process_id])

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "company_id": self.company_id,
            "process_id": self.process_id,
            "link_type": self.link_type,
            "target_ref_type": self.target_ref_type,
            "target_ref_id": self.target_ref_id,
            "target_key": self.target_key,
            "target_payload": self.target_payload_json or {},
            "contribution_type": self.contribution_type,
            "contribution_weight": _decimal(self.contribution_weight),
            "notes": self.notes,
            "created_by_user_id": self.created_by_user_id,
            "updated_by_user_id": self.updated_by_user_id,
            "created_at": _iso(self.created_at),
            "updated_at": _iso(self.updated_at),
        }


class IndicatorLineOfSight(db.Model):
    """Linha de visada entre indicador de processo e indicador corporativo."""

    __tablename__ = "indicator_line_of_sight"
    __table_args__ = (
        db.UniqueConstraint(
            "company_id",
            "process_indicator_id",
            "corporate_indicator_id",
            name="uq_indicator_line_of_sight_company_pair",
        ),
        db.ForeignKeyConstraint(
            ["company_id", "process_indicator_id"],
            ["indicators.company_id", "indicators.id"],
            ondelete="CASCADE",
            name="fk_indicator_los_company_process_indicator",
        ),
        db.ForeignKeyConstraint(
            ["company_id", "corporate_indicator_id"],
            ["indicators.company_id", "indicators.id"],
            ondelete="CASCADE",
            name="fk_indicator_los_company_corporate_indicator",
        ),
        db.CheckConstraint(
            f"relationship_type IN {INDICATOR_LINE_OF_SIGHT_RELATIONSHIP_TYPES}",
            name="ck_indicator_line_of_sight_relationship_type",
        ),
        db.Index("ix_indicator_los_company_process_indicator", "company_id", "process_indicator_id"),
        db.Index("ix_indicator_los_company_corporate_indicator", "company_id", "corporate_indicator_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    process_indicator_id = db.Column(db.Integer, nullable=False, index=True)
    corporate_indicator_id = db.Column(db.Integer, nullable=False, index=True)
    relationship_type = db.Column(db.String(40), nullable=False, default="contributes_to")
    contribution_weight = db.Column(db.Numeric(7, 4))
    notes = db.Column(db.Text)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    updated_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    company = db.relationship("Company", foreign_keys=[company_id])
    process_indicator = db.relationship("Indicator", foreign_keys=[process_indicator_id])
    corporate_indicator = db.relationship("Indicator", foreign_keys=[corporate_indicator_id])

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "company_id": self.company_id,
            "process_indicator_id": self.process_indicator_id,
            "corporate_indicator_id": self.corporate_indicator_id,
            "relationship_type": self.relationship_type,
            "contribution_weight": _decimal(self.contribution_weight),
            "notes": self.notes,
            "created_by_user_id": self.created_by_user_id,
            "updated_by_user_id": self.updated_by_user_id,
            "created_at": _iso(self.created_at),
            "updated_at": _iso(self.updated_at),
        }


__all__ = [
    "INDICATOR_LINE_OF_SIGHT_RELATIONSHIP_TYPES",
    "PROCESS_MATURITY_LEVEL_VALUES",
    "PROCESS_STRATEGIC_CRITICALITY_VALUES",
    "STRATEGY_ALIGNMENT_LINK_TYPES",
    "STRATEGY_ALIGNMENT_TARGET_REF_TYPES",
    "IndicatorLineOfSight",
    "OrganizationalIdentity",
    "ProcessStrategicAlignmentLink",
    "ProcessStrategyProfile",
]
