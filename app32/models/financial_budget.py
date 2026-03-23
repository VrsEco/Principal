from __future__ import annotations

from datetime import datetime

from sqlalchemy.dialects.postgresql import JSONB

from . import db
from .financial import MOVEMENT_NATURE_VALUES


BUDGET_VERSION_STATUS_VALUES = ("draft", "active", "archived")
BUDGET_VERSION_SCENARIO_VALUES = ("original", "forecast", "reforecast")
BUDGET_LINE_VIEW_VALUES = ("competence", "due", "cash")


class FinancialBudgetVersion(db.Model):
    __tablename__ = "financial_budget_versions"
    __table_args__ = (
        db.UniqueConstraint("company_id", "code", name="uq_financial_budget_versions_company_code"),
        db.CheckConstraint(
            f"status IN {BUDGET_VERSION_STATUS_VALUES}",
            name="ck_financial_budget_versions_status",
        ),
        db.CheckConstraint(
            f"scenario_type IN {BUDGET_VERSION_SCENARIO_VALUES}",
            name="ck_financial_budget_versions_scenario_type",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    code = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String(160), nullable=False)
    scenario_type = db.Column(db.String(20), nullable=False, default="original", index=True)
    status = db.Column(db.String(20), nullable=False, default="draft", index=True)
    period_start = db.Column(db.Date, nullable=False, index=True)
    period_end = db.Column(db.Date, nullable=False, index=True)
    notes = db.Column(db.Text)
    metadata_json = db.Column(JSONB, nullable=False, default=dict)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    approved_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    approved_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = db.Column(db.DateTime)

    created_by_user = db.relationship("User", foreign_keys=[created_by_user_id])
    approved_by_user = db.relationship("User", foreign_keys=[approved_by_user_id])
    lines = db.relationship(
        "FinancialBudgetLine",
        backref="version",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "code": self.code,
            "name": self.name,
            "scenario_type": self.scenario_type,
            "status": self.status,
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
            "notes": self.notes,
            "metadata_json": self.metadata_json or {},
            "created_by_user_id": self.created_by_user_id,
            "approved_by_user_id": self.approved_by_user_id,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class FinancialBudgetLine(db.Model):
    __tablename__ = "financial_budget_lines"
    __table_args__ = (
        db.UniqueConstraint(
            "company_id",
            "budget_version_id",
            "line_code",
            name="uq_financial_budget_lines_company_version_code",
        ),
        db.CheckConstraint(
            f"budget_view IN {BUDGET_LINE_VIEW_VALUES}",
            name="ck_financial_budget_lines_budget_view",
        ),
        db.CheckConstraint(
            f"movement_nature IN {MOVEMENT_NATURE_VALUES}",
            name="ck_financial_budget_lines_movement_nature",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    budget_version_id = db.Column(
        db.Integer,
        db.ForeignKey("financial_budget_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    line_code = db.Column(db.String(50), nullable=False)
    line_name = db.Column(db.String(160), nullable=False)
    line_order = db.Column(db.Integer, nullable=False, default=100, index=True)
    budget_view = db.Column(db.String(20), nullable=False, default="competence", index=True)
    movement_nature = db.Column(db.String(10), nullable=False, default="debit", index=True)
    chart_account_id = db.Column(db.Integer, db.ForeignKey("financial_chart_accounts.id"), index=True)
    cost_center_id = db.Column(db.Integer, db.ForeignKey("financial_cost_centers.id"), index=True)
    activity_id = db.Column(db.Integer, db.ForeignKey("process_routines.id"), index=True)
    process_instance_id = db.Column(db.Integer, db.ForeignKey("process_instances.id"), index=True)
    routine_id = db.Column(db.Integer, db.ForeignKey("routines.id"), index=True)
    notes = db.Column(db.Text)
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    metadata_json = db.Column(JSONB, nullable=False, default=dict)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = db.Column(db.DateTime)

    chart_account = db.relationship("FinancialChartAccount", foreign_keys=[chart_account_id])
    cost_center = db.relationship("FinancialCostCenter", foreign_keys=[cost_center_id])
    activity = db.relationship("ProcessRoutine", foreign_keys=[activity_id])
    process_instance = db.relationship("ProcessInstance", foreign_keys=[process_instance_id])
    routine = db.relationship("Routine", foreign_keys=[routine_id])
    amounts = db.relationship(
        "FinancialBudgetAmount",
        backref="line",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "budget_version_id": self.budget_version_id,
            "line_code": self.line_code,
            "line_name": self.line_name,
            "line_order": self.line_order,
            "budget_view": self.budget_view,
            "movement_nature": self.movement_nature,
            "chart_account_id": self.chart_account_id,
            "cost_center_id": self.cost_center_id,
            "activity_id": self.activity_id,
            "process_instance_id": self.process_instance_id,
            "routine_id": self.routine_id,
            "notes": self.notes,
            "is_active": self.is_active,
            "metadata_json": self.metadata_json or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class FinancialBudgetAmount(db.Model):
    __tablename__ = "financial_budget_amounts"
    __table_args__ = (
        db.UniqueConstraint(
            "company_id",
            "budget_line_id",
            "period_month",
            name="uq_financial_budget_amounts_company_line_month",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    budget_line_id = db.Column(
        db.Integer,
        db.ForeignKey("financial_budget_lines.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    period_month = db.Column(db.Date, nullable=False, index=True)
    budget_amount = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    notes = db.Column(db.Text)
    metadata_json = db.Column(JSONB, nullable=False, default=dict)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = db.Column(db.DateTime)

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "budget_line_id": self.budget_line_id,
            "period_month": self.period_month.isoformat() if self.period_month else None,
            "budget_amount": float(self.budget_amount or 0),
            "notes": self.notes,
            "metadata_json": self.metadata_json or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
