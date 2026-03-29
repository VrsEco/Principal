from __future__ import annotations

from datetime import datetime

from sqlalchemy.dialects.postgresql import JSONB

from . import db
from .financial import MOVEMENT_NATURE_VALUES


BUDGET_CYCLE_STATUS_VALUES = ("draft", "active", "archived")
BUDGET_VERSION_STATUS_VALUES = ("draft", "active", "archived")
BUDGET_VERSION_SCENARIO_VALUES = ("original", "forecast", "reforecast")
BUDGET_CATEGORY_VALUES = ("general", "capex", "opex", "capex_extra", "custom")
BUDGET_LINE_VIEW_VALUES = ("competence", "due", "cash")
BUDGET_CONTRACT_STATUS_VALUES = ("draft", "active", "closed", "cancelled")
BUDGET_DOCUMENT_STATUS_VALUES = ("draft", "registered", "scheduled", "partially_scheduled", "fully_scheduled", "cancelled")
BUDGET_DOCUMENT_TYPE_VALUES = ("invoice", "equivalent")


class FinancialBudgetCycle(db.Model):
    __tablename__ = "financial_budget_cycles"
    __table_args__ = (
        db.UniqueConstraint("company_id", "year", name="uq_financial_budget_cycles_company_year"),
        db.UniqueConstraint("company_id", "code", name="uq_financial_budget_cycles_company_code"),
        db.CheckConstraint(
            f"status IN {BUDGET_CYCLE_STATUS_VALUES}",
            name="ck_financial_budget_cycles_status",
        ),
        db.CheckConstraint("year >= 2000", name="ck_financial_budget_cycles_year"),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    code = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String(160), nullable=False)
    year = db.Column(db.Integer, nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False, default="draft", index=True)
    notes = db.Column(db.Text)
    metadata_json = db.Column(JSONB, nullable=False, default=dict)
    company_code_snapshot = db.Column(db.String(20), index=True)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    approved_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    approved_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = db.Column(db.DateTime)

    created_by_user = db.relationship("User", foreign_keys=[created_by_user_id])
    approved_by_user = db.relationship("User", foreign_keys=[approved_by_user_id])
    versions = db.relationship(
        "FinancialBudgetVersion",
        backref="budget_cycle",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "code": self.code,
            "name": self.name,
            "year": self.year,
            "status": self.status,
            "notes": self.notes,
            "metadata_json": self.metadata_json or {},
            "company_code_snapshot": self.company_code_snapshot,
            "created_by_user_id": self.created_by_user_id,
            "approved_by_user_id": self.approved_by_user_id,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class FinancialBudgetVersion(db.Model):
    __tablename__ = "financial_budget_versions"
    __table_args__ = (
        db.UniqueConstraint("company_id", "code", name="uq_financial_budget_versions_company_code"),
        db.UniqueConstraint(
            "company_id",
            "budget_cycle_id",
            "budget_category",
            "budget_seq",
            name="uq_financial_budget_versions_company_cycle_category_seq",
        ),
        db.UniqueConstraint("company_id", "full_code", name="uq_financial_budget_versions_company_full_code"),
        db.CheckConstraint(
            f"status IN {BUDGET_VERSION_STATUS_VALUES}",
            name="ck_financial_budget_versions_status",
        ),
        db.CheckConstraint(
            f"scenario_type IN {BUDGET_VERSION_SCENARIO_VALUES}",
            name="ck_financial_budget_versions_scenario_type",
        ),
        db.CheckConstraint(
            f"budget_category IN {BUDGET_CATEGORY_VALUES}",
            name="ck_financial_budget_versions_budget_category",
        ),
        db.CheckConstraint("budget_seq IS NULL OR budget_seq >= 1", name="ck_financial_budget_versions_budget_seq"),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    budget_cycle_id = db.Column(db.Integer, db.ForeignKey("financial_budget_cycles.id"), index=True)
    code = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String(160), nullable=False)
    budget_category = db.Column(db.String(24), nullable=False, default="general", index=True)
    budget_seq = db.Column(db.Integer, index=True)
    full_code = db.Column(db.String(200), index=True)
    company_code_snapshot = db.Column(db.String(20), index=True)
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
            "budget_cycle_id": self.budget_cycle_id,
            "code": self.code,
            "name": self.name,
            "budget_category": self.budget_category,
            "budget_seq": self.budget_seq,
            "full_code": self.full_code,
            "company_code_snapshot": self.company_code_snapshot,
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
        db.UniqueConstraint(
            "company_id",
            "budget_version_id",
            "line_seq",
            name="uq_financial_budget_lines_company_version_seq",
        ),
        db.UniqueConstraint("company_id", "full_code", name="uq_financial_budget_lines_company_full_code"),
        db.CheckConstraint(
            f"budget_view IN {BUDGET_LINE_VIEW_VALUES}",
            name="ck_financial_budget_lines_budget_view",
        ),
        db.CheckConstraint(
            f"movement_nature IN {MOVEMENT_NATURE_VALUES}",
            name="ck_financial_budget_lines_movement_nature",
        ),
        db.CheckConstraint(
            "planned_amount >= 0",
            name="ck_financial_budget_lines_planned_amount_nonneg",
        ),
        db.CheckConstraint("line_seq IS NULL OR line_seq >= 1", name="ck_financial_budget_lines_line_seq"),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    budget_version_id = db.Column(
        db.Integer,
        db.ForeignKey("financial_budget_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    line_code = db.Column(db.String(60), nullable=False)
    line_name = db.Column(db.String(160), nullable=False)
    line_seq = db.Column(db.Integer, index=True)
    full_code = db.Column(db.String(200), index=True)
    company_code_snapshot = db.Column(db.String(20), index=True)
    line_order = db.Column(db.Integer, nullable=False, default=100, index=True)
    budget_view = db.Column(db.String(20), nullable=False, default="competence", index=True)
    movement_nature = db.Column(db.String(10), nullable=False, default="debit", index=True)
    planned_amount = db.Column(db.Numeric(14, 2), nullable=False, default=0)
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
    contracts = db.relationship(
        "FinancialBudgetContract",
        backref="budget_line",
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
            "line_seq": self.line_seq,
            "full_code": self.full_code,
            "company_code_snapshot": self.company_code_snapshot,
            "line_order": self.line_order,
            "budget_view": self.budget_view,
            "movement_nature": self.movement_nature,
            "planned_amount": float(self.planned_amount or 0),
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


class FinancialBudgetContract(db.Model):
    __tablename__ = "financial_budget_contracts"
    __table_args__ = (
        db.UniqueConstraint("company_id", "contract_code", name="uq_financial_budget_contracts_company_code"),
        db.UniqueConstraint(
            "company_id",
            "budget_line_id",
            "contract_seq",
            name="uq_financial_budget_contracts_company_line_seq",
        ),
        db.UniqueConstraint("company_id", "full_code", name="uq_financial_budget_contracts_company_full_code"),
        db.CheckConstraint(
            f"status IN {BUDGET_CONTRACT_STATUS_VALUES}",
            name="ck_financial_budget_contracts_status",
        ),
        db.CheckConstraint(
            "contract_amount >= 0",
            name="ck_financial_budget_contracts_amount_nonneg",
        ),
        db.CheckConstraint("contract_seq IS NULL OR contract_seq >= 1", name="ck_financial_budget_contracts_contract_seq"),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    budget_line_id = db.Column(
        db.Integer,
        db.ForeignKey("financial_budget_lines.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    contract_code = db.Column(db.String(60), nullable=False)
    name = db.Column(db.String(160), nullable=False)
    contract_seq = db.Column(db.Integer, index=True)
    full_code = db.Column(db.String(200), index=True)
    company_code_snapshot = db.Column(db.String(20), index=True)
    status = db.Column(db.String(20), nullable=False, default="draft", index=True)
    contract_amount = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    counterparty_id = db.Column(db.Integer, db.ForeignKey("financial_counterparties.id"), index=True)
    signed_at = db.Column(db.Date)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    notes = db.Column(db.Text)
    metadata_json = db.Column(JSONB, nullable=False, default=dict)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = db.Column(db.DateTime)

    counterparty = db.relationship("FinancialCounterparty", foreign_keys=[counterparty_id])
    documents = db.relationship(
        "FinancialBudgetDocument",
        backref="budget_contract",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "budget_line_id": self.budget_line_id,
            "contract_code": self.contract_code,
            "name": self.name,
            "contract_seq": self.contract_seq,
            "full_code": self.full_code,
            "company_code_snapshot": self.company_code_snapshot,
            "status": self.status,
            "contract_amount": float(self.contract_amount or 0),
            "counterparty_id": self.counterparty_id,
            "signed_at": self.signed_at.isoformat() if self.signed_at else None,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "notes": self.notes,
            "metadata_json": self.metadata_json or {},
            "created_by_user_id": self.created_by_user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class FinancialBudgetDocument(db.Model):
    __tablename__ = "financial_budget_documents"
    __table_args__ = (
        db.UniqueConstraint("company_id", "document_code", name="uq_financial_budget_documents_company_code"),
        db.UniqueConstraint(
            "company_id",
            "budget_contract_id",
            "document_seq",
            name="uq_financial_budget_documents_company_contract_seq",
        ),
        db.UniqueConstraint("company_id", "full_code", name="uq_financial_budget_documents_company_full_code"),
        db.CheckConstraint(
            f"status IN {BUDGET_DOCUMENT_STATUS_VALUES}",
            name="ck_financial_budget_documents_status",
        ),
        db.CheckConstraint(
            f"document_type IN {BUDGET_DOCUMENT_TYPE_VALUES}",
            name="ck_financial_budget_documents_type",
        ),
        db.CheckConstraint(
            "document_amount >= 0",
            name="ck_financial_budget_documents_amount_nonneg",
        ),
        db.CheckConstraint("document_seq IS NULL OR document_seq >= 1", name="ck_financial_budget_documents_document_seq"),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    budget_contract_id = db.Column(
        db.Integer,
        db.ForeignKey("financial_budget_contracts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_code = db.Column(db.String(60), nullable=False)
    title = db.Column(db.String(160), nullable=False)
    document_seq = db.Column(db.Integer, index=True)
    full_code = db.Column(db.String(200), index=True)
    company_code_snapshot = db.Column(db.String(20), index=True)
    document_type = db.Column(db.String(20), nullable=False, default="invoice", index=True)
    status = db.Column(db.String(30), nullable=False, default="registered", index=True)
    document_number = db.Column(db.String(80))
    document_amount = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    issue_date = db.Column(db.Date)
    competence_date = db.Column(db.Date)
    counterparty_id = db.Column(db.Integer, db.ForeignKey("financial_counterparties.id"), index=True)
    is_default_suggestion = db.Column(db.Boolean, nullable=False, default=False, index=True)
    notes = db.Column(db.Text)
    metadata_json = db.Column(JSONB, nullable=False, default=dict)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = db.Column(db.DateTime)

    counterparty = db.relationship("FinancialCounterparty", foreign_keys=[counterparty_id])
    schedules = db.relationship(
        "FinancialSchedule",
        backref="budget_document",
        lazy="dynamic",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "budget_contract_id": self.budget_contract_id,
            "document_code": self.document_code,
            "title": self.title,
            "document_seq": self.document_seq,
            "full_code": self.full_code,
            "company_code_snapshot": self.company_code_snapshot,
            "document_type": self.document_type,
            "status": self.status,
            "document_number": self.document_number,
            "document_amount": float(self.document_amount or 0),
            "issue_date": self.issue_date.isoformat() if self.issue_date else None,
            "competence_date": self.competence_date.isoformat() if self.competence_date else None,
            "counterparty_id": self.counterparty_id,
            "is_default_suggestion": self.is_default_suggestion,
            "notes": self.notes,
            "metadata_json": self.metadata_json or {},
            "created_by_user_id": self.created_by_user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
