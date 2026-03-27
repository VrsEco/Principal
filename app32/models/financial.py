from datetime import datetime

from sqlalchemy.dialects.postgresql import JSONB

from . import db


ENTRY_TYPE_VALUES = (
    "payable",
    "receivable",
    "bank_movement",
    "transfer",
    "adjustment",
    "forecast",
)

MOVEMENT_NATURE_VALUES = ("debit", "credit")

ENTRY_STATUS_VALUES = (
    "draft",
    "pending_review",
    "scheduled",
    "posted",
    "partially_settled",
    "settled",
    "cancelled",
)

ENTRY_ORIGIN_VALUES = (
    "manual",
    "process",
    "routine",
    "sapiens",
    "ofx",
    "csv",
    "xls",
    "csc",
    "api",
    "mcp",
    "migration",
)

REVIEW_STATUS_VALUES = (
    "pending_review",
    "suggested_by_ai",
    "reviewed",
    "approved",
    "rejected",
)

ALLOCATION_TYPE_VALUES = ("percentage", "amount")

SETTLEMENT_TYPE_VALUES = (
    "manual",
    "bank_import",
    "api",
    "mcp",
    "automatic_process",
    "automatic_rule",
    "reversal",
)

SETTLEMENT_STATUS_VALUES = ("draft", "posted", "reversed", "cancelled")

RECONCILIATION_STATUS_VALUES = ("pending", "suggested", "matched", "reconciled", "rejected")
MATCH_STATUS_VALUES = ("suggested", "confirmed", "rejected")
CLASSIFICATION_OPERATOR_VALUES = ("contains", "equals", "starts_with")
CLASSIFICATION_MEMORY_SOURCE_VALUES = ("user_confirmed", "ai_suggested", "imported_memory")
CLASSIFICATION_SUGGESTION_SOURCE_VALUES = ("rule", "memory", "ai")
CLASSIFICATION_SUGGESTION_STATUS_VALUES = ("suggested", "confirmed", "rejected", "applied")

IMPORT_SOURCE_VALUES = ("csv", "csc", "xlsx", "ofx", "api", "mcp")
IMPORT_BATCH_STATUS_VALUES = ("uploaded", "parsed", "processed", "processed_with_errors", "cancelled")
IMPORT_ROW_STATUS_VALUES = ("staged", "validated", "rejected", "imported")
CHART_ACCOUNT_KIND_VALUES = ("asset", "liability", "equity", "revenue", "expense", "result")
CLOSING_STATUS_VALUES = ("draft", "closed", "reopened")
SCHEDULE_FREQUENCY_VALUES = ("one_time", "weekly", "monthly", "yearly")
SCHEDULE_STATUS_VALUES = ("draft", "active", "paused", "completed", "cancelled")
AUTOMATION_TRIGGER_STATUS_VALUES = ("pending", "in_progress", "completed", "overdue", "any")
AUTOMATION_EXECUTION_STATUS_VALUES = ("success", "skipped", "error")
DOMAIN_ENABLEMENT_TYPE_VALUES = ("project", "process")
INGESTION_SOURCE_VALUES = (
    "manual",
    "import_csv",
    "import_xlsx",
    "import_ofx",
    "import_csc",
    "api",
    "mcp",
    "sapiens_image",
    "sapiens_document",
    "bank_reconciliation",
    "integration_erp",
)
INGESTION_COMPLETION_STATUS_VALUES = (
    "received",
    "parsed",
    "normalized",
    "draft",
    "partial",
    "classified_partial",
    "classified_complete",
    "review_required",
    "approved",
    "reconciled",
    "settled",
    "closed",
    "rejected",
)
INGESTION_REVIEW_STATUS_VALUES = ("not_required", "pending_review", "reviewed", "rejected")
INGESTION_CONFIDENCE_LEVEL_VALUES = ("high", "medium", "low")


class FinancialBankAccount(db.Model):
    __tablename__ = "financial_bank_accounts"
    __table_args__ = (
        db.UniqueConstraint("company_id", "code", name="uq_financial_bank_accounts_company_code"),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    code = db.Column(db.String(30), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    bank_code = db.Column(db.String(20))
    bank_name = db.Column(db.String(120))
    branch_number = db.Column(db.String(20))
    account_number = db.Column(db.String(30))
    account_digit = db.Column(db.String(10))
    holder_name = db.Column(db.String(255))
    holder_document = db.Column(db.String(50))
    pix_key = db.Column(db.String(120))
    currency_code = db.Column(db.String(3), nullable=False, default="BRL")
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    metadata_json = db.Column(JSONB, nullable=False, default=dict)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = db.Column(db.DateTime)

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "code": self.code,
            "name": self.name,
            "bank_code": self.bank_code,
            "bank_name": self.bank_name,
            "branch_number": self.branch_number,
            "account_number": self.account_number,
            "account_digit": self.account_digit,
            "holder_name": self.holder_name,
            "holder_document": self.holder_document,
            "pix_key": self.pix_key,
            "currency_code": self.currency_code,
            "is_active": self.is_active,
            "metadata_json": self.metadata_json or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class FinancialChartAccount(db.Model):
    __tablename__ = "financial_chart_accounts"
    __table_args__ = (
        db.UniqueConstraint("company_id", "code", name="uq_financial_chart_accounts_company_code"),
        db.CheckConstraint(
            f"account_kind IN {CHART_ACCOUNT_KIND_VALUES}",
            name="ck_financial_chart_accounts_kind",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    parent_id = db.Column(db.Integer, db.ForeignKey("financial_chart_accounts.id"), index=True)
    code = db.Column(db.String(30), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    account_kind = db.Column(db.String(20), nullable=False, default="expense", index=True)
    movement_nature = db.Column(db.String(10), index=True)
    accepts_posting = db.Column(db.Boolean, nullable=False, default=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    metadata_json = db.Column(JSONB, nullable=False, default=dict)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = db.Column(db.DateTime)

    parent = db.relationship("FinancialChartAccount", remote_side=[id], foreign_keys=[parent_id])

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "parent_id": self.parent_id,
            "code": self.code,
            "name": self.name,
            "account_kind": self.account_kind,
            "movement_nature": self.movement_nature,
            "accepts_posting": self.accepts_posting,
            "is_active": self.is_active,
            "metadata_json": self.metadata_json or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class FinancialCostCenter(db.Model):
    __tablename__ = "financial_cost_centers"
    __table_args__ = (
        db.UniqueConstraint("company_id", "code", name="uq_financial_cost_centers_company_code"),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    parent_id = db.Column(db.Integer, db.ForeignKey("financial_cost_centers.id"), index=True)
    manager_employee_id = db.Column(db.Integer, db.ForeignKey("employees.id"), index=True)
    code = db.Column(db.String(30), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    metadata_json = db.Column(JSONB, nullable=False, default=dict)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = db.Column(db.DateTime)

    parent = db.relationship("FinancialCostCenter", remote_side=[id], foreign_keys=[parent_id])

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "parent_id": self.parent_id,
            "manager_employee_id": self.manager_employee_id,
            "code": self.code,
            "name": self.name,
            "description": self.description,
            "is_active": self.is_active,
            "metadata_json": self.metadata_json or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class FinancialCounterparty(db.Model):
    __tablename__ = "financial_counterparties"
    __table_args__ = (
        db.UniqueConstraint("company_id", "code", name="uq_financial_counterparties_company_code"),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    default_chart_account_id = db.Column(db.Integer, db.ForeignKey("financial_chart_accounts.id"), index=True)
    default_cost_center_id = db.Column(db.Integer, db.ForeignKey("financial_cost_centers.id"), index=True)
    code = db.Column(db.String(30), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    legal_name = db.Column(db.String(255))
    document_number = db.Column(db.String(50), index=True)
    email = db.Column(db.String(255))
    phone = db.Column(db.String(50))
    pix_key = db.Column(db.String(120))
    notes = db.Column(db.Text)
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    metadata_json = db.Column(JSONB, nullable=False, default=dict)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = db.Column(db.DateTime)

    default_chart_account = db.relationship("FinancialChartAccount", foreign_keys=[default_chart_account_id])
    default_cost_center = db.relationship("FinancialCostCenter", foreign_keys=[default_cost_center_id])

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "default_chart_account_id": self.default_chart_account_id,
            "default_cost_center_id": self.default_cost_center_id,
            "code": self.code,
            "name": self.name,
            "legal_name": self.legal_name,
            "document_number": self.document_number,
            "email": self.email,
            "phone": self.phone,
            "pix_key": self.pix_key,
            "notes": self.notes,
            "is_active": self.is_active,
            "metadata_json": self.metadata_json or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class FinancialAccountCategory(db.Model):
    __tablename__ = "financial_account_categories"
    __table_args__ = (
        db.UniqueConstraint("company_id", "code", name="uq_financial_account_categories_company_code"),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    code = db.Column(db.String(30), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    metadata_json = db.Column(JSONB, nullable=False, default=dict)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = db.Column(db.DateTime)

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "code": self.code,
            "name": self.name,
            "description": self.description,
            "is_active": self.is_active,
            "metadata_json": self.metadata_json or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class FinancialPaymentTerm(db.Model):
    __tablename__ = "financial_payment_terms"
    __table_args__ = (
        db.UniqueConstraint("company_id", "code", name="uq_financial_payment_terms_company_code"),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    code = db.Column(db.String(30), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    metadata_json = db.Column(JSONB, nullable=False, default=dict)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = db.Column(db.DateTime)

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "code": self.code,
            "name": self.name,
            "description": self.description,
            "is_active": self.is_active,
            "metadata_json": self.metadata_json or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class FinancialAssetAccount(db.Model):
    __tablename__ = "financial_asset_accounts"
    __table_args__ = (
        db.UniqueConstraint("company_id", "code", name="uq_financial_asset_accounts_company_code"),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    code = db.Column(db.String(30), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    metadata_json = db.Column(JSONB, nullable=False, default=dict)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = db.Column(db.DateTime)

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "code": self.code,
            "name": self.name,
            "description": self.description,
            "is_active": self.is_active,
            "metadata_json": self.metadata_json or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class FinancialCorrectionIndex(db.Model):
    __tablename__ = "financial_correction_indexes"
    __table_args__ = (
        db.UniqueConstraint("company_id", "code", name="uq_financial_correction_indexes_company_code"),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    code = db.Column(db.String(30), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    metadata_json = db.Column(JSONB, nullable=False, default=dict)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = db.Column(db.DateTime)

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "code": self.code,
            "name": self.name,
            "description": self.description,
            "is_active": self.is_active,
            "metadata_json": self.metadata_json or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class FinancialDiscountRule(db.Model):
    __tablename__ = "financial_discount_rules"
    __table_args__ = (
        db.UniqueConstraint("company_id", "code", name="uq_financial_discount_rules_company_code"),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    code = db.Column(db.String(30), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    metadata_json = db.Column(JSONB, nullable=False, default=dict)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = db.Column(db.DateTime)

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "code": self.code,
            "name": self.name,
            "description": self.description,
            "is_active": self.is_active,
            "metadata_json": self.metadata_json or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class FinancialPaymentMethod(db.Model):
    __tablename__ = "financial_payment_methods"
    __table_args__ = (
        db.UniqueConstraint("company_id", "code", name="uq_financial_payment_methods_company_code"),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    code = db.Column(db.String(30), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    metadata_json = db.Column(JSONB, nullable=False, default=dict)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = db.Column(db.DateTime)

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "code": self.code,
            "name": self.name,
            "description": self.description,
            "is_active": self.is_active,
            "metadata_json": self.metadata_json or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class FinancialDomainEnablement(db.Model):
    __tablename__ = "financial_domain_enablements"
    __table_args__ = (
        db.UniqueConstraint(
            "company_id",
            "domain_type",
            "source_id",
            name="uq_financial_domain_enablements_source",
        ),
        db.CheckConstraint(
            f"domain_type IN {DOMAIN_ENABLEMENT_TYPE_VALUES}",
            name="ck_financial_domain_enablements_domain_type",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    domain_type = db.Column(db.String(20), nullable=False, index=True)
    source_id = db.Column(db.Integer, nullable=False, index=True)
    is_enabled = db.Column(db.Boolean, nullable=False, default=True, index=True)
    notes = db.Column(db.Text)
    metadata_json = db.Column(JSONB, nullable=False, default=dict)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = db.Column(db.DateTime)

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "domain_type": self.domain_type,
            "source_id": self.source_id,
            "is_enabled": self.is_enabled,
            "notes": self.notes,
            "metadata_json": self.metadata_json or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class FinancialClosing(db.Model):
    __tablename__ = "financial_closings"
    __table_args__ = (
        db.UniqueConstraint("company_id", "period_start", "period_end", name="uq_financial_closings_period"),
        db.CheckConstraint(
            f"status IN {CLOSING_STATUS_VALUES}",
            name="ck_financial_closings_status",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    period_start = db.Column(db.Date, nullable=False, index=True)
    period_end = db.Column(db.Date, nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False, default="draft", index=True)
    notes = db.Column(db.Text)
    summary_json = db.Column(JSONB, nullable=False, default=dict)
    closed_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    closed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = db.Column(db.DateTime)

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
            "status": self.status,
            "notes": self.notes,
            "summary_json": self.summary_json or {},
            "closed_by_user_id": self.closed_by_user_id,
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class FinancialSchedule(db.Model):
    __tablename__ = "financial_schedules"
    __table_args__ = (
        db.UniqueConstraint("company_id", "schedule_code", name="uq_financial_schedules_company_code"),
        db.CheckConstraint(
            f"entry_type IN {ENTRY_TYPE_VALUES}",
            name="ck_financial_schedules_entry_type",
        ),
        db.CheckConstraint(
            f"movement_nature IN {MOVEMENT_NATURE_VALUES}",
            name="ck_financial_schedules_movement_nature",
        ),
        db.CheckConstraint(
            f"origin_type IN {ENTRY_ORIGIN_VALUES}",
            name="ck_financial_schedules_origin_type",
        ),
        db.CheckConstraint(
            f"frequency IN {SCHEDULE_FREQUENCY_VALUES}",
            name="ck_financial_schedules_frequency",
        ),
        db.CheckConstraint(
            f"status IN {SCHEDULE_STATUS_VALUES}",
            name="ck_financial_schedules_status",
        ),
        db.CheckConstraint("template_amount >= 0", name="ck_financial_schedules_amount_nonneg"),
        db.CheckConstraint("interval_value >= 1", name="ck_financial_schedules_interval_positive"),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    schedule_code = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    entry_type = db.Column(db.String(30), nullable=False, index=True)
    movement_nature = db.Column(db.String(10), nullable=False, index=True)
    origin_type = db.Column(db.String(30), nullable=False, default="manual", index=True)
    status = db.Column(db.String(20), nullable=False, default="draft", index=True)
    frequency = db.Column(db.String(20), nullable=False, default="monthly", index=True)
    interval_value = db.Column(db.Integer, nullable=False, default=1)
    start_date = db.Column(db.Date, nullable=False, index=True)
    end_date = db.Column(db.Date, index=True)
    first_due_date = db.Column(db.Date, nullable=False, index=True)
    next_due_date = db.Column(db.Date, nullable=False, index=True)
    day_of_month = db.Column(db.Integer)
    weekday = db.Column(db.Integer)
    description = db.Column(db.String(255), nullable=False)
    memo = db.Column(db.Text)
    document_number_prefix = db.Column(db.String(40))
    template_amount = db.Column(db.Numeric(14, 2), nullable=False)
    currency_code = db.Column(db.String(3), nullable=False, default="BRL")
    auto_post = db.Column(db.Boolean, nullable=False, default=False)
    generate_advance_days = db.Column(db.Integer, nullable=False, default=0)
    bank_account_id = db.Column(db.Integer, index=True)
    counterparty_id = db.Column(db.Integer, index=True)
    chart_account_id = db.Column(db.Integer, index=True)
    cost_center_id = db.Column(db.Integer, index=True)
    budget_document_id = db.Column(db.Integer, db.ForeignKey("financial_budget_documents.id"), index=True)
    activity_id = db.Column(db.Integer, db.ForeignKey("process_routines.id"), index=True)
    process_instance_id = db.Column(db.Integer, db.ForeignKey("process_instances.id"), index=True)
    routine_id = db.Column(db.Integer, db.ForeignKey("routines.id"), index=True)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_by_employee_id = db.Column(db.Integer, db.ForeignKey("employees.id"))
    created_by_agent = db.Column(db.String(50))
    notes = db.Column(db.Text)
    metadata_json = db.Column(JSONB, nullable=False, default=dict)
    last_generated_at = db.Column(db.DateTime)
    last_generated_entry_id = db.Column(db.Integer, db.ForeignKey("financial_entries.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = db.Column(db.DateTime)

    process_instance = db.relationship("ProcessInstance", foreign_keys=[process_instance_id])
    routine = db.relationship("Routine", foreign_keys=[routine_id])
    activity = db.relationship("ProcessRoutine", foreign_keys=[activity_id])
    last_generated_entry = db.relationship("FinancialEntry", foreign_keys=[last_generated_entry_id])

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "schedule_code": self.schedule_code,
            "name": self.name,
            "entry_type": self.entry_type,
            "movement_nature": self.movement_nature,
            "origin_type": self.origin_type,
            "status": self.status,
            "frequency": self.frequency,
            "interval_value": self.interval_value,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "first_due_date": self.first_due_date.isoformat() if self.first_due_date else None,
            "next_due_date": self.next_due_date.isoformat() if self.next_due_date else None,
            "day_of_month": self.day_of_month,
            "weekday": self.weekday,
            "description": self.description,
            "memo": self.memo,
            "document_number_prefix": self.document_number_prefix,
            "template_amount": float(self.template_amount or 0),
            "currency_code": self.currency_code,
            "auto_post": self.auto_post,
            "generate_advance_days": self.generate_advance_days,
            "bank_account_id": self.bank_account_id,
            "counterparty_id": self.counterparty_id,
            "chart_account_id": self.chart_account_id,
            "cost_center_id": self.cost_center_id,
            "budget_document_id": self.budget_document_id,
            "activity_id": self.activity_id,
            "process_instance_id": self.process_instance_id,
            "routine_id": self.routine_id,
            "created_by_user_id": self.created_by_user_id,
            "created_by_employee_id": self.created_by_employee_id,
            "created_by_agent": self.created_by_agent,
            "notes": self.notes,
            "metadata_json": self.metadata_json or {},
            "last_generated_at": self.last_generated_at.isoformat() if self.last_generated_at else None,
            "last_generated_entry_id": self.last_generated_entry_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class FinancialAutomationRule(db.Model):
    __tablename__ = "financial_automation_rules"
    __table_args__ = (
        db.UniqueConstraint("company_id", "rule_code", name="uq_financial_automation_rules_company_code"),
        db.CheckConstraint(
            f"entry_type IN {ENTRY_TYPE_VALUES}",
            name="ck_financial_automation_rules_entry_type",
        ),
        db.CheckConstraint(
            f"movement_nature IN {MOVEMENT_NATURE_VALUES}",
            name="ck_financial_automation_rules_movement_nature",
        ),
        db.CheckConstraint(
            f"origin_type IN {ENTRY_ORIGIN_VALUES}",
            name="ck_financial_automation_rules_origin_type",
        ),
        db.CheckConstraint(
            f"frequency IN {SCHEDULE_FREQUENCY_VALUES}",
            name="ck_financial_automation_rules_frequency",
        ),
        db.CheckConstraint(
            f"trigger_status IN {AUTOMATION_TRIGGER_STATUS_VALUES}",
            name="ck_financial_automation_rules_trigger_status",
        ),
        db.CheckConstraint("template_amount >= 0", name="ck_financial_automation_rules_amount_nonneg"),
        db.CheckConstraint("interval_value >= 1", name="ck_financial_automation_rules_interval_positive"),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    rule_code = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    process_id = db.Column(db.Integer, db.ForeignKey("processes.id"), index=True)
    activity_id = db.Column(db.Integer, db.ForeignKey("process_routines.id"), index=True)
    trigger_status = db.Column(db.String(20), nullable=False, default="any", index=True)
    trigger_on_create = db.Column(db.Boolean, nullable=False, default=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    auto_activate_schedule = db.Column(db.Boolean, nullable=False, default=True)
    schedule_name_template = db.Column(db.String(160), nullable=False)
    description_template = db.Column(db.String(255), nullable=False)
    entry_type = db.Column(db.String(30), nullable=False, default="forecast")
    movement_nature = db.Column(db.String(10), nullable=False)
    origin_type = db.Column(db.String(30), nullable=False, default="process")
    frequency = db.Column(db.String(20), nullable=False, default="one_time")
    interval_value = db.Column(db.Integer, nullable=False, default=1)
    start_offset_days = db.Column(db.Integer, nullable=False, default=0)
    due_offset_days = db.Column(db.Integer, nullable=False, default=0)
    template_amount = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    currency_code = db.Column(db.String(3), nullable=False, default="BRL")
    auto_post = db.Column(db.Boolean, nullable=False, default=False)
    generate_advance_days = db.Column(db.Integer, nullable=False, default=0)
    bank_account_id = db.Column(db.Integer, index=True)
    counterparty_id = db.Column(db.Integer, index=True)
    chart_account_id = db.Column(db.Integer, index=True)
    cost_center_id = db.Column(db.Integer, index=True)
    routine_id = db.Column(db.Integer, db.ForeignKey("routines.id"), index=True)
    notes = db.Column(db.Text)
    metadata_json = db.Column(JSONB, nullable=False, default=dict)
    last_execution_at = db.Column(db.DateTime)
    last_generated_schedule_id = db.Column(db.Integer, db.ForeignKey("financial_schedules.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = db.Column(db.DateTime)

    process = db.relationship("Process", foreign_keys=[process_id])
    activity = db.relationship("ProcessRoutine", foreign_keys=[activity_id])
    routine = db.relationship("Routine", foreign_keys=[routine_id])
    last_generated_schedule = db.relationship("FinancialSchedule", foreign_keys=[last_generated_schedule_id])

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "rule_code": self.rule_code,
            "name": self.name,
            "process_id": self.process_id,
            "activity_id": self.activity_id,
            "trigger_status": self.trigger_status,
            "trigger_on_create": self.trigger_on_create,
            "is_active": self.is_active,
            "auto_activate_schedule": self.auto_activate_schedule,
            "schedule_name_template": self.schedule_name_template,
            "description_template": self.description_template,
            "entry_type": self.entry_type,
            "movement_nature": self.movement_nature,
            "origin_type": self.origin_type,
            "frequency": self.frequency,
            "interval_value": self.interval_value,
            "start_offset_days": self.start_offset_days,
            "due_offset_days": self.due_offset_days,
            "template_amount": float(self.template_amount or 0),
            "currency_code": self.currency_code,
            "auto_post": self.auto_post,
            "generate_advance_days": self.generate_advance_days,
            "bank_account_id": self.bank_account_id,
            "counterparty_id": self.counterparty_id,
            "chart_account_id": self.chart_account_id,
            "cost_center_id": self.cost_center_id,
            "routine_id": self.routine_id,
            "notes": self.notes,
            "metadata_json": self.metadata_json or {},
            "last_execution_at": self.last_execution_at.isoformat() if self.last_execution_at else None,
            "last_generated_schedule_id": self.last_generated_schedule_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class FinancialAutomationExecution(db.Model):
    __tablename__ = "financial_automation_executions"
    __table_args__ = (
        db.UniqueConstraint(
            "company_id",
            "rule_id",
            "process_instance_id",
            "idempotency_key",
            "attempt_number",
            name="uq_financial_automation_executions_idempotency",
        ),
        db.CheckConstraint(
            f"execution_status IN {AUTOMATION_EXECUTION_STATUS_VALUES}",
            name="ck_financial_automation_executions_status",
        ),
        db.CheckConstraint("attempt_number >= 1", name="ck_financial_automation_executions_attempt_positive"),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    rule_id = db.Column(db.Integer, db.ForeignKey("financial_automation_rules.id"), nullable=False, index=True)
    process_instance_id = db.Column(db.Integer, db.ForeignKey("process_instances.id"), nullable=False, index=True)
    schedule_id = db.Column(db.Integer, db.ForeignKey("financial_schedules.id"), index=True)
    trigger_status = db.Column(db.String(20), nullable=False, index=True)
    idempotency_key = db.Column(db.String(160), nullable=False)
    execution_status = db.Column(db.String(20), nullable=False, default="success", index=True)
    attempt_number = db.Column(db.Integer, nullable=False, default=1)
    error_message = db.Column(db.Text)
    payload_json = db.Column(JSONB, nullable=False, default=dict)
    executed_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    rule = db.relationship("FinancialAutomationRule", foreign_keys=[rule_id])
    process_instance = db.relationship("ProcessInstance", foreign_keys=[process_instance_id])
    schedule = db.relationship("FinancialSchedule", foreign_keys=[schedule_id])

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "rule_id": self.rule_id,
            "process_instance_id": self.process_instance_id,
            "schedule_id": self.schedule_id,
            "trigger_status": self.trigger_status,
            "idempotency_key": self.idempotency_key,
            "execution_status": self.execution_status,
            "attempt_number": self.attempt_number,
            "error_message": self.error_message,
            "payload_json": self.payload_json or {},
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class FinancialEntry(db.Model):
    __tablename__ = "financial_entries"
    __table_args__ = (
        db.UniqueConstraint("company_id", "entry_code", name="uq_financial_entries_company_code"),
        db.CheckConstraint("original_amount >= 0", name="ck_financial_entries_original_amount_nonneg"),
        db.CheckConstraint(
            f"entry_type IN {ENTRY_TYPE_VALUES}",
            name="ck_financial_entries_entry_type",
        ),
        db.CheckConstraint(
            f"movement_nature IN {MOVEMENT_NATURE_VALUES}",
            name="ck_financial_entries_movement_nature",
        ),
        db.CheckConstraint(
            f"status IN {ENTRY_STATUS_VALUES}",
            name="ck_financial_entries_status",
        ),
        db.CheckConstraint(
            f"origin_type IN {ENTRY_ORIGIN_VALUES}",
            name="ck_financial_entries_origin_type",
        ),
        db.CheckConstraint(
            f"review_status IN {REVIEW_STATUS_VALUES}",
            name="ck_financial_entries_review_status",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    entry_code = db.Column(db.String(50), nullable=False)

    entry_type = db.Column(db.String(30), nullable=False, index=True)
    movement_nature = db.Column(db.String(10), nullable=False, index=True)
    status = db.Column(db.String(30), nullable=False, default="draft", index=True)
    origin_type = db.Column(db.String(30), nullable=False, default="manual", index=True)

    description = db.Column(db.String(255), nullable=False)
    memo = db.Column(db.Text)
    document_number = db.Column(db.String(80))
    external_reference = db.Column(db.String(120))
    origin_reference = db.Column(db.String(120))

    issue_date = db.Column(db.Date)
    competence_date = db.Column(db.Date, nullable=False, index=True)
    due_date = db.Column(db.Date, index=True)
    occurred_on = db.Column(db.Date)

    original_amount = db.Column(db.Numeric(14, 2), nullable=False)
    currency_code = db.Column(db.String(3), nullable=False, default="BRL")

    bank_account_id = db.Column(db.Integer, index=True)
    counterparty_id = db.Column(db.Integer, index=True)
    chart_account_id = db.Column(db.Integer, index=True)
    cost_center_id = db.Column(db.Integer, index=True)

    activity_id = db.Column(db.Integer, db.ForeignKey("process_routines.id"), index=True)
    process_instance_id = db.Column(db.Integer, db.ForeignKey("process_instances.id"), index=True)
    routine_id = db.Column(db.Integer, db.ForeignKey("routines.id"), index=True)

    review_status = db.Column(db.String(30), nullable=False, default="pending_review", index=True)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_by_employee_id = db.Column(db.Integer, db.ForeignKey("employees.id"))
    created_by_agent = db.Column(db.String(50))
    approved_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    approved_at = db.Column(db.DateTime)
    notes = db.Column(db.Text)
    metadata_json = db.Column(JSONB, nullable=False, default=dict)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = db.Column(db.DateTime)

    allocations = db.relationship(
        "FinancialEntryAllocation",
        backref="entry",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    settlements = db.relationship(
        "FinancialSettlement",
        backref="entry",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    process_instance = db.relationship("ProcessInstance", foreign_keys=[process_instance_id])
    routine = db.relationship("Routine", foreign_keys=[routine_id])
    activity = db.relationship("ProcessRoutine", foreign_keys=[activity_id])

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "entry_code": self.entry_code,
            "entry_type": self.entry_type,
            "movement_nature": self.movement_nature,
            "status": self.status,
            "origin_type": self.origin_type,
            "description": self.description,
            "memo": self.memo,
            "document_number": self.document_number,
            "external_reference": self.external_reference,
            "origin_reference": self.origin_reference,
            "issue_date": self.issue_date.isoformat() if self.issue_date else None,
            "competence_date": self.competence_date.isoformat() if self.competence_date else None,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "occurred_on": self.occurred_on.isoformat() if self.occurred_on else None,
            "original_amount": float(self.original_amount or 0),
            "currency_code": self.currency_code,
            "bank_account_id": self.bank_account_id,
            "counterparty_id": self.counterparty_id,
            "chart_account_id": self.chart_account_id,
            "cost_center_id": self.cost_center_id,
            "budget_document_id": self.budget_document_id,
            "activity_id": self.activity_id,
            "process_instance_id": self.process_instance_id,
            "routine_id": self.routine_id,
            "review_status": self.review_status,
            "created_by_user_id": self.created_by_user_id,
            "created_by_employee_id": self.created_by_employee_id,
            "created_by_agent": self.created_by_agent,
            "approved_by_user_id": self.approved_by_user_id,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "notes": self.notes,
            "metadata_json": self.metadata_json or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class FinancialEntryAllocation(db.Model):
    __tablename__ = "financial_entry_allocations"
    __table_args__ = (
        db.CheckConstraint(
            f"allocation_type IN {ALLOCATION_TYPE_VALUES}",
            name="ck_financial_entry_allocations_type",
        ),
        db.CheckConstraint(
            "(percentage IS NULL OR percentage >= 0) AND (allocated_amount IS NULL OR allocated_amount >= 0)",
            name="ck_financial_entry_allocations_nonneg",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    financial_entry_id = db.Column(
        db.Integer, db.ForeignKey("financial_entries.id", ondelete="CASCADE"), nullable=False, index=True
    )

    chart_account_id = db.Column(db.Integer, index=True)
    cost_center_id = db.Column(db.Integer, index=True)
    activity_id = db.Column(db.Integer, db.ForeignKey("process_routines.id"), index=True)
    process_instance_id = db.Column(db.Integer, db.ForeignKey("process_instances.id"), index=True)
    routine_id = db.Column(db.Integer, db.ForeignKey("routines.id"), index=True)

    allocation_type = db.Column(db.String(20), nullable=False)
    percentage = db.Column(db.Numeric(7, 4))
    allocated_amount = db.Column(db.Numeric(14, 2))

    notes = db.Column(db.Text)
    metadata_json = db.Column(JSONB, nullable=False, default=dict)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = db.Column(db.DateTime)

    process_instance = db.relationship("ProcessInstance", foreign_keys=[process_instance_id])
    routine = db.relationship("Routine", foreign_keys=[routine_id])
    activity = db.relationship("ProcessRoutine", foreign_keys=[activity_id])

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "financial_entry_id": self.financial_entry_id,
            "chart_account_id": self.chart_account_id,
            "cost_center_id": self.cost_center_id,
            "activity_id": self.activity_id,
            "process_instance_id": self.process_instance_id,
            "routine_id": self.routine_id,
            "allocation_type": self.allocation_type,
            "percentage": float(self.percentage) if self.percentage is not None else None,
            "allocated_amount": float(self.allocated_amount) if self.allocated_amount is not None else None,
            "notes": self.notes,
            "metadata_json": self.metadata_json or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class FinancialSettlement(db.Model):
    __tablename__ = "financial_settlements"
    __table_args__ = (
        db.UniqueConstraint("company_id", "settlement_code", name="uq_financial_settlements_company_code"),
        db.CheckConstraint(
            f"settlement_type IN {SETTLEMENT_TYPE_VALUES}",
            name="ck_financial_settlements_type",
        ),
        db.CheckConstraint(
            f"settlement_status IN {SETTLEMENT_STATUS_VALUES}",
            name="ck_financial_settlements_status",
        ),
        db.CheckConstraint(
            f"reconciliation_status IN {RECONCILIATION_STATUS_VALUES}",
            name="ck_financial_settlements_reconciliation_status",
        ),
        db.CheckConstraint(
            """
            principal_amount >= 0 AND interest_amount >= 0 AND penalty_amount >= 0
            AND discount_amount >= 0 AND fee_amount >= 0 AND other_adjustments_amount >= 0
            AND net_amount >= 0
            """,
            name="ck_financial_settlements_amounts_nonneg",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    financial_entry_id = db.Column(
        db.Integer, db.ForeignKey("financial_entries.id", ondelete="CASCADE"), nullable=False, index=True
    )
    settlement_code = db.Column(db.String(50), nullable=False)

    settlement_type = db.Column(db.String(30), nullable=False)
    settlement_status = db.Column(db.String(30), nullable=False, default="posted")
    settlement_date = db.Column(db.Date, nullable=False, index=True)
    bank_account_id = db.Column(db.Integer, index=True)

    principal_amount = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    interest_amount = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    penalty_amount = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    discount_amount = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    fee_amount = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    other_adjustments_amount = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    net_amount = db.Column(db.Numeric(14, 2), nullable=False)

    external_reference = db.Column(db.String(120))
    import_batch_id = db.Column(db.Integer, index=True)
    reconciliation_status = db.Column(db.String(30), nullable=False, default="pending", index=True)

    notes = db.Column(db.Text)
    metadata_json = db.Column(JSONB, nullable=False, default=dict)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_by_employee_id = db.Column(db.Integer, db.ForeignKey("employees.id"))
    created_by_agent = db.Column(db.String(50))

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = db.Column(db.DateTime)

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "financial_entry_id": self.financial_entry_id,
            "settlement_code": self.settlement_code,
            "settlement_type": self.settlement_type,
            "settlement_status": self.settlement_status,
            "settlement_date": self.settlement_date.isoformat() if self.settlement_date else None,
            "bank_account_id": self.bank_account_id,
            "principal_amount": float(self.principal_amount or 0),
            "interest_amount": float(self.interest_amount or 0),
            "penalty_amount": float(self.penalty_amount or 0),
            "discount_amount": float(self.discount_amount or 0),
            "fee_amount": float(self.fee_amount or 0),
            "other_adjustments_amount": float(self.other_adjustments_amount or 0),
            "net_amount": float(self.net_amount or 0),
            "external_reference": self.external_reference,
            "import_batch_id": self.import_batch_id,
            "reconciliation_status": self.reconciliation_status,
            "notes": self.notes,
            "metadata_json": self.metadata_json or {},
            "created_by_user_id": self.created_by_user_id,
            "created_by_employee_id": self.created_by_employee_id,
            "created_by_agent": self.created_by_agent,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class FinancialImportBatch(db.Model):
    __tablename__ = "financial_import_batches"
    __table_args__ = (
        db.UniqueConstraint("company_id", "batch_code", name="uq_financial_import_batches_company_code"),
        db.CheckConstraint(
            f"source_type IN {IMPORT_SOURCE_VALUES}",
            name="ck_financial_import_batches_source_type",
        ),
        db.CheckConstraint(
            f"status IN {IMPORT_BATCH_STATUS_VALUES}",
            name="ck_financial_import_batches_status",
        ),
        db.CheckConstraint("total_rows >= 0", name="ck_financial_import_batches_total_rows_nonneg"),
        db.CheckConstraint("valid_rows >= 0", name="ck_financial_import_batches_valid_rows_nonneg"),
        db.CheckConstraint("error_rows >= 0", name="ck_financial_import_batches_error_rows_nonneg"),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    batch_code = db.Column(db.String(50), nullable=False)
    source_type = db.Column(db.String(20), nullable=False, index=True)
    status = db.Column(db.String(30), nullable=False, default="uploaded", index=True)

    file_name = db.Column(db.String(255))
    file_hash = db.Column(db.String(64), index=True)
    imported_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    finished_at = db.Column(db.DateTime)

    total_rows = db.Column(db.Integer, nullable=False, default=0)
    valid_rows = db.Column(db.Integer, nullable=False, default=0)
    error_rows = db.Column(db.Integer, nullable=False, default=0)

    uploaded_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    uploaded_by_employee_id = db.Column(db.Integer, db.ForeignKey("employees.id"))
    created_by_agent = db.Column(db.String(50))
    notes = db.Column(db.Text)
    metadata_json = db.Column(JSONB, nullable=False, default=dict)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = db.Column(db.DateTime)

    rows = db.relationship(
        "FinancialImportRow",
        backref="batch",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "batch_code": self.batch_code,
            "source_type": self.source_type,
            "status": self.status,
            "file_name": self.file_name,
            "file_hash": self.file_hash,
            "imported_at": self.imported_at.isoformat() if self.imported_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "total_rows": self.total_rows,
            "valid_rows": self.valid_rows,
            "error_rows": self.error_rows,
            "uploaded_by_user_id": self.uploaded_by_user_id,
            "uploaded_by_employee_id": self.uploaded_by_employee_id,
            "created_by_agent": self.created_by_agent,
            "notes": self.notes,
            "metadata_json": self.metadata_json or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class FinancialImportRow(db.Model):
    __tablename__ = "financial_import_rows"
    __table_args__ = (
        db.CheckConstraint(
            f"processing_status IN {IMPORT_ROW_STATUS_VALUES}",
            name="ck_financial_import_rows_processing_status",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    import_batch_id = db.Column(
        db.Integer, db.ForeignKey("financial_import_batches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    row_number = db.Column(db.Integer, nullable=False)
    processing_status = db.Column(db.String(20), nullable=False, default="staged", index=True)

    document_number = db.Column(db.String(80))
    description = db.Column(db.String(255))
    occurred_on = db.Column(db.Date)
    due_date = db.Column(db.Date)
    amount = db.Column(db.Numeric(14, 2))
    movement_nature = db.Column(db.String(10))
    bank_reference = db.Column(db.String(120))
    counterparty_name = db.Column(db.String(255))

    raw_payload = db.Column(JSONB, nullable=False, default=dict)
    normalized_payload = db.Column(JSONB, nullable=False, default=dict)
    error_message = db.Column(db.Text)
    matched_entry_id = db.Column(db.Integer, db.ForeignKey("financial_entries.id"), index=True)
    created_entry_id = db.Column(db.Integer, db.ForeignKey("financial_entries.id"), index=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = db.Column(db.DateTime)

    matched_entry = db.relationship("FinancialEntry", foreign_keys=[matched_entry_id])
    created_entry = db.relationship("FinancialEntry", foreign_keys=[created_entry_id])

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "import_batch_id": self.import_batch_id,
            "row_number": self.row_number,
            "processing_status": self.processing_status,
            "document_number": self.document_number,
            "description": self.description,
            "occurred_on": self.occurred_on.isoformat() if self.occurred_on else None,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "amount": float(self.amount) if self.amount is not None else None,
            "movement_nature": self.movement_nature,
            "bank_reference": self.bank_reference,
            "counterparty_name": self.counterparty_name,
            "raw_payload": self.raw_payload or {},
            "normalized_payload": self.normalized_payload or {},
            "error_message": self.error_message,
            "matched_entry_id": self.matched_entry_id,
            "created_entry_id": self.created_entry_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class FinancialReconciliationMatch(db.Model):
    __tablename__ = "financial_reconciliation_matches"
    __table_args__ = (
        db.CheckConstraint(
            f"match_status IN {MATCH_STATUS_VALUES}",
            name="ck_financial_reconciliation_matches_status",
        ),
        db.CheckConstraint(
            "(confidence_score IS NULL) OR (confidence_score >= 0 AND confidence_score <= 1)",
            name="ck_financial_reconciliation_matches_confidence",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    import_batch_id = db.Column(db.Integer, db.ForeignKey("financial_import_batches.id", ondelete="CASCADE"), nullable=False, index=True)
    import_row_id = db.Column(db.Integer, db.ForeignKey("financial_import_rows.id", ondelete="CASCADE"), nullable=False, index=True)
    financial_entry_id = db.Column(db.Integer, db.ForeignKey("financial_entries.id", ondelete="CASCADE"), nullable=False, index=True)

    match_status = db.Column(db.String(20), nullable=False, default="suggested", index=True)
    confidence_score = db.Column(db.Numeric(5, 4))
    match_reason = db.Column(db.String(255))
    matched_amount = db.Column(db.Numeric(14, 2))
    matched_date = db.Column(db.Date)
    metadata_json = db.Column(JSONB, nullable=False, default=dict)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = db.Column(db.DateTime)

    import_batch = db.relationship("FinancialImportBatch", foreign_keys=[import_batch_id])
    import_row = db.relationship("FinancialImportRow", foreign_keys=[import_row_id])
    financial_entry = db.relationship("FinancialEntry", foreign_keys=[financial_entry_id])

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "import_batch_id": self.import_batch_id,
            "import_row_id": self.import_row_id,
            "financial_entry_id": self.financial_entry_id,
            "match_status": self.match_status,
            "confidence_score": float(self.confidence_score) if self.confidence_score is not None else None,
            "match_reason": self.match_reason,
            "matched_amount": float(self.matched_amount) if self.matched_amount is not None else None,
            "matched_date": self.matched_date.isoformat() if self.matched_date else None,
            "metadata_json": self.metadata_json or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class FinancialClassificationRule(db.Model):
    __tablename__ = "financial_classification_rules"
    __table_args__ = (
        db.CheckConstraint(
            f"operator IN {CLASSIFICATION_OPERATOR_VALUES}",
            name="ck_financial_classification_rules_operator",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    priority = db.Column(db.Integer, nullable=False, default=100, index=True)

    source_type = db.Column(db.String(20), index=True)
    field_name = db.Column(db.String(50), nullable=False)
    operator = db.Column(db.String(20), nullable=False, default="contains")
    match_value = db.Column(db.String(255), nullable=False)

    entry_type = db.Column(db.String(30))
    movement_nature = db.Column(db.String(10))
    chart_account_id = db.Column(db.Integer, index=True)
    cost_center_id = db.Column(db.Integer, index=True)
    activity_id = db.Column(db.Integer, db.ForeignKey("process_routines.id"), index=True)
    process_instance_id = db.Column(db.Integer, db.ForeignKey("process_instances.id"), index=True)
    routine_id = db.Column(db.Integer, db.ForeignKey("routines.id"), index=True)
    counterparty_hint = db.Column(db.String(255))
    notes = db.Column(db.Text)
    metadata_json = db.Column(JSONB, nullable=False, default=dict)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = db.Column(db.DateTime)

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "name": self.name,
            "is_active": self.is_active,
            "priority": self.priority,
            "source_type": self.source_type,
            "field_name": self.field_name,
            "operator": self.operator,
            "match_value": self.match_value,
            "entry_type": self.entry_type,
            "movement_nature": self.movement_nature,
            "chart_account_id": self.chart_account_id,
            "cost_center_id": self.cost_center_id,
            "activity_id": self.activity_id,
            "process_instance_id": self.process_instance_id,
            "routine_id": self.routine_id,
            "counterparty_hint": self.counterparty_hint,
            "notes": self.notes,
            "metadata_json": self.metadata_json or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class FinancialClassificationMemory(db.Model):
    __tablename__ = "financial_classification_memories"
    __table_args__ = (
        db.CheckConstraint(
            f"source IN {CLASSIFICATION_MEMORY_SOURCE_VALUES}",
            name="ck_financial_classification_memories_source",
        ),
        db.CheckConstraint(
            "(confidence_score IS NULL) OR (confidence_score >= 0 AND confidence_score <= 1)",
            name="ck_financial_classification_memories_confidence",
        ),
        db.CheckConstraint("times_confirmed >= 0", name="ck_financial_classification_memories_times_confirmed_nonneg"),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    supplier_name = db.Column(db.String(255), index=True)
    supplier_document = db.Column(db.String(50), index=True)
    description_pattern = db.Column(db.String(255), index=True)
    product_hint = db.Column(db.String(255))
    amount_range_min = db.Column(db.Numeric(14, 2))
    amount_range_max = db.Column(db.Numeric(14, 2))

    entry_type = db.Column(db.String(30))
    movement_nature = db.Column(db.String(10))
    chart_account_id = db.Column(db.Integer, index=True)
    cost_center_id = db.Column(db.Integer, index=True)
    activity_id = db.Column(db.Integer, db.ForeignKey("process_routines.id"), index=True)
    process_instance_id = db.Column(db.Integer, db.ForeignKey("process_instances.id"), index=True)
    routine_id = db.Column(db.Integer, db.ForeignKey("routines.id"), index=True)
    counterparty_hint = db.Column(db.String(255))

    confidence_score = db.Column(db.Numeric(5, 4))
    times_confirmed = db.Column(db.Integer, nullable=False, default=0)
    last_confirmed_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    last_confirmed_at = db.Column(db.DateTime)
    source = db.Column(db.String(30), nullable=False, default="user_confirmed", index=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    metadata_json = db.Column(JSONB, nullable=False, default=dict)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = db.Column(db.DateTime)

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "supplier_name": self.supplier_name,
            "supplier_document": self.supplier_document,
            "description_pattern": self.description_pattern,
            "product_hint": self.product_hint,
            "amount_range_min": float(self.amount_range_min) if self.amount_range_min is not None else None,
            "amount_range_max": float(self.amount_range_max) if self.amount_range_max is not None else None,
            "entry_type": self.entry_type,
            "movement_nature": self.movement_nature,
            "chart_account_id": self.chart_account_id,
            "cost_center_id": self.cost_center_id,
            "activity_id": self.activity_id,
            "process_instance_id": self.process_instance_id,
            "routine_id": self.routine_id,
            "counterparty_hint": self.counterparty_hint,
            "confidence_score": float(self.confidence_score) if self.confidence_score is not None else None,
            "times_confirmed": self.times_confirmed,
            "last_confirmed_by_user_id": self.last_confirmed_by_user_id,
            "last_confirmed_at": self.last_confirmed_at.isoformat() if self.last_confirmed_at else None,
            "source": self.source,
            "is_active": self.is_active,
            "metadata_json": self.metadata_json or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class FinancialClassificationSuggestion(db.Model):
    __tablename__ = "financial_classification_suggestions"
    __table_args__ = (
        db.CheckConstraint(
            f"source_layer IN {CLASSIFICATION_SUGGESTION_SOURCE_VALUES}",
            name="ck_financial_classification_suggestions_source_layer",
        ),
        db.CheckConstraint(
            f"status IN {CLASSIFICATION_SUGGESTION_STATUS_VALUES}",
            name="ck_financial_classification_suggestions_status",
        ),
        db.CheckConstraint(
            "(score IS NULL) OR (score >= 0 AND score <= 1)",
            name="ck_financial_classification_suggestions_score",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    import_batch_id = db.Column(db.Integer, db.ForeignKey("financial_import_batches.id", ondelete="CASCADE"), nullable=False, index=True)
    import_row_id = db.Column(db.Integer, db.ForeignKey("financial_import_rows.id", ondelete="CASCADE"), nullable=False, index=True)
    rank_position = db.Column(db.Integer, nullable=False, default=1)
    source_layer = db.Column(db.String(20), nullable=False, default="memory")
    score = db.Column(db.Numeric(5, 4))
    reason = db.Column(db.String(255))
    suggested_payload_json = db.Column(JSONB, nullable=False, default=dict)
    status = db.Column(db.String(20), nullable=False, default="suggested", index=True)
    confirmed_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    confirmed_at = db.Column(db.DateTime)
    metadata_json = db.Column(JSONB, nullable=False, default=dict)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = db.Column(db.DateTime)

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "import_batch_id": self.import_batch_id,
            "import_row_id": self.import_row_id,
            "rank_position": self.rank_position,
            "source_layer": self.source_layer,
            "score": float(self.score) if self.score is not None else None,
            "reason": self.reason,
            "suggested_payload_json": self.suggested_payload_json or {},
            "status": self.status,
            "confirmed_by_user_id": self.confirmed_by_user_id,
            "confirmed_at": self.confirmed_at.isoformat() if self.confirmed_at else None,
            "metadata_json": self.metadata_json or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class FinancialIngestionRecord(db.Model):
    __tablename__ = "financial_ingestion_records"
    __table_args__ = (
        db.CheckConstraint(
            f"origin_type IN {INGESTION_SOURCE_VALUES}",
            name="ck_financial_ingestion_records_origin_type",
        ),
        db.CheckConstraint(
            f"completion_status IN {INGESTION_COMPLETION_STATUS_VALUES}",
            name="ck_financial_ingestion_records_completion_status",
        ),
        db.CheckConstraint(
            f"review_status IN {INGESTION_REVIEW_STATUS_VALUES}",
            name="ck_financial_ingestion_records_review_status",
        ),
        db.CheckConstraint(
            "(confidence_score IS NULL) OR (confidence_score >= 0 AND confidence_score <= 1)",
            name="ck_financial_ingestion_records_confidence_score",
        ),
        db.CheckConstraint(
            "(confidence_level IS NULL) OR (confidence_level IN ('high', 'medium', 'low'))",
            name="ck_financial_ingestion_records_confidence_level",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    origin_type = db.Column(db.String(30), nullable=False, index=True)
    origin_reference = db.Column(db.String(120), index=True)
    external_system = db.Column(db.String(80), index=True)
    source_file_name = db.Column(db.String(255))
    source_mime_type = db.Column(db.String(120))
    source_channel = db.Column(db.String(50), index=True)
    import_batch_id = db.Column(db.Integer, db.ForeignKey("financial_import_batches.id"), index=True)
    related_schedule_id = db.Column(db.Integer, db.ForeignKey("financial_schedules.id"), index=True)
    related_entry_id = db.Column(db.Integer, db.ForeignKey("financial_entries.id"), index=True)
    completion_status = db.Column(db.String(30), nullable=False, default="received", index=True)
    review_status = db.Column(db.String(30), nullable=False, default="pending_review", index=True)
    confidence_score = db.Column(db.Numeric(5, 4))
    confidence_level = db.Column(db.String(10), index=True)
    raw_payload_json = db.Column(JSONB, nullable=False, default=dict)
    normalized_payload_json = db.Column(JSONB, nullable=False, default=dict)
    extracted_text = db.Column(db.Text)
    llm_response_json = db.Column(JSONB, nullable=False, default=dict)
    review_notes = db.Column(db.Text)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)
    reviewed_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)
    reviewed_at = db.Column(db.DateTime)
    metadata_json = db.Column(JSONB, nullable=False, default=dict)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = db.Column(db.DateTime)

    import_batch = db.relationship("FinancialImportBatch", foreign_keys=[import_batch_id])
    related_schedule = db.relationship("FinancialSchedule", foreign_keys=[related_schedule_id])
    related_entry = db.relationship("FinancialEntry", foreign_keys=[related_entry_id])

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "origin_type": self.origin_type,
            "origin_reference": self.origin_reference,
            "external_system": self.external_system,
            "source_file_name": self.source_file_name,
            "source_mime_type": self.source_mime_type,
            "source_channel": self.source_channel,
            "import_batch_id": self.import_batch_id,
            "related_schedule_id": self.related_schedule_id,
            "related_entry_id": self.related_entry_id,
            "completion_status": self.completion_status,
            "review_status": self.review_status,
            "confidence_score": float(self.confidence_score) if self.confidence_score is not None else None,
            "confidence_level": self.confidence_level,
            "raw_payload_json": self.raw_payload_json or {},
            "normalized_payload_json": self.normalized_payload_json or {},
            "extracted_text": self.extracted_text,
            "llm_response_json": self.llm_response_json or {},
            "review_notes": self.review_notes,
            "created_by_user_id": self.created_by_user_id,
            "reviewed_by_user_id": self.reviewed_by_user_id,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "metadata_json": self.metadata_json or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
