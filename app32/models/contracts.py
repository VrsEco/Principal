from __future__ import annotations

from datetime import datetime

from sqlalchemy.dialects.postgresql import JSONB

from . import db


class ContractParty(db.Model):
    __tablename__ = "contract_parties"
    __table_args__ = (
        db.UniqueConstraint("company_id", "code", name="uq_contract_parties_company_code"),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    financial_counterparty_id = db.Column(db.Integer, db.ForeignKey("financial_counterparties.id"), index=True)
    code = db.Column(db.String(30), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    legal_name = db.Column(db.String(255))
    document_type = db.Column(db.String(20))
    document_number = db.Column(db.String(50), index=True)
    email = db.Column(db.String(255))
    phone = db.Column(db.String(50))
    is_customer = db.Column(db.Boolean, nullable=False, default=False, index=True)
    is_supplier = db.Column(db.Boolean, nullable=False, default=False, index=True)
    status = db.Column(db.String(30), nullable=False, default="active", index=True)
    notes = db.Column(db.Text)
    metadata_json = db.Column(JSONB, nullable=False, default=dict)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)
    updated_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = db.Column(db.DateTime)

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "financial_counterparty_id": self.financial_counterparty_id,
            "code": self.code,
            "name": self.name,
            "legal_name": self.legal_name,
            "document_type": self.document_type,
            "document_number": self.document_number,
            "email": self.email,
            "phone": self.phone,
            "is_customer": bool(self.is_customer),
            "is_supplier": bool(self.is_supplier),
            "status": self.status,
            "notes": self.notes,
            "metadata_json": self.metadata_json or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ContractCatalogItem(db.Model):
    __tablename__ = "contract_catalog_items"
    __table_args__ = (
        db.UniqueConstraint("company_id", "code", name="uq_contract_catalog_items_company_code"),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    parent_id = db.Column(db.Integer, db.ForeignKey("contract_catalog_items.id"), index=True)
    code = db.Column(db.String(30), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    item_kind = db.Column(db.String(30), nullable=False, default="service", index=True)
    description = db.Column(db.Text)
    unit_code = db.Column(db.String(20))
    accepts_contracting = db.Column(db.Boolean, nullable=False, default=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    metadata_json = db.Column(JSONB, nullable=False, default=dict)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = db.Column(db.DateTime)

    parent = db.relationship("ContractCatalogItem", remote_side=[id], foreign_keys=[parent_id])

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "parent_id": self.parent_id,
            "code": self.code,
            "name": self.name,
            "item_kind": self.item_kind,
            "description": self.description,
            "unit_code": self.unit_code,
            "accepts_contracting": bool(self.accepts_contracting),
            "is_active": bool(self.is_active),
            "metadata_json": self.metadata_json or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Contract(db.Model):
    __tablename__ = "contracts"
    __table_args__ = (
        db.UniqueConstraint("company_id", "code", name="uq_contracts_company_code"),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    party_id = db.Column(db.Integer, db.ForeignKey("contract_parties.id"), nullable=False, index=True)
    code = db.Column(db.String(30), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(30), nullable=False, default="draft", index=True)
    contract_type = db.Column(db.String(60))
    currency_code = db.Column(db.String(3), nullable=False, default="BRL")
    signed_at = db.Column(db.Date)
    service_start_at = db.Column(db.Date)
    service_end_at = db.Column(db.Date)
    billing_start_at = db.Column(db.Date)
    billing_end_at = db.Column(db.Date)
    last_billing_at = db.Column(db.Date)
    periodicity = db.Column(db.String(30))
    competence_rule = db.Column(db.String(60))
    due_rule = db.Column(db.String(60))
    renewal_rule = db.Column(db.String(60))
    notes = db.Column(db.Text)
    version = db.Column(db.Integer, nullable=False, default=1)
    metadata_json = db.Column(JSONB, nullable=False, default=dict)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)
    updated_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = db.Column(db.DateTime)

    party = db.relationship("ContractParty", foreign_keys=[party_id])
    items = db.relationship("ContractItem", backref="contract", lazy="dynamic", cascade="all, delete-orphan")
    billing_items = db.relationship("ContractBillingItem", backref="contract", lazy="dynamic", cascade="all, delete-orphan")
    retentions = db.relationship("ContractRetention", backref="contract", lazy="dynamic", cascade="all, delete-orphan")
    triggers = db.relationship("ContractTrigger", backref="contract", lazy="dynamic", cascade="all, delete-orphan")
    documents = db.relationship("ContractDocument", backref="contract", lazy="dynamic", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "party_id": self.party_id,
            "code": self.code,
            "title": self.title,
            "status": self.status,
            "contract_type": self.contract_type,
            "currency_code": self.currency_code,
            "signed_at": self.signed_at.isoformat() if self.signed_at else None,
            "service_start_at": self.service_start_at.isoformat() if self.service_start_at else None,
            "service_end_at": self.service_end_at.isoformat() if self.service_end_at else None,
            "billing_start_at": self.billing_start_at.isoformat() if self.billing_start_at else None,
            "billing_end_at": self.billing_end_at.isoformat() if self.billing_end_at else None,
            "last_billing_at": self.last_billing_at.isoformat() if self.last_billing_at else None,
            "periodicity": self.periodicity,
            "competence_rule": self.competence_rule,
            "due_rule": self.due_rule,
            "renewal_rule": self.renewal_rule,
            "notes": self.notes,
            "version": self.version,
            "metadata_json": self.metadata_json or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ContractItem(db.Model):
    __tablename__ = "contract_items"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    contract_id = db.Column(db.Integer, db.ForeignKey("contracts.id"), nullable=False, index=True)
    contract_catalog_item_id = db.Column(db.Integer, db.ForeignKey("contract_catalog_items.id"), index=True)
    item_code = db.Column(db.String(30))
    item_type = db.Column(db.String(40))
    description = db.Column(db.Text, nullable=False)
    quantity = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    unit_code = db.Column(db.String(20))
    unit_price = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    total_price = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    order_index = db.Column(db.Integer, nullable=False, default=0)
    notes = db.Column(db.Text)
    metadata_json = db.Column(JSONB, nullable=False, default=dict)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    contract_catalog_item = db.relationship("ContractCatalogItem", foreign_keys=[contract_catalog_item_id])

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "contract_id": self.contract_id,
            "contract_catalog_item_id": self.contract_catalog_item_id,
            "item_code": self.item_code,
            "item_type": self.item_type,
            "description": self.description,
            "quantity": float(self.quantity or 0),
            "unit_code": self.unit_code,
            "unit_price": float(self.unit_price or 0),
            "total_price": float(self.total_price or 0),
            "order_index": self.order_index,
            "notes": self.notes,
            "metadata_json": self.metadata_json or {},
        }


class ContractBillingItem(db.Model):
    __tablename__ = "contract_billing_items"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    contract_id = db.Column(db.Integer, db.ForeignKey("contracts.id"), nullable=False, index=True)
    contract_item_id = db.Column(db.Integer, db.ForeignKey("contract_items.id"), index=True)
    billing_code = db.Column(db.String(30))
    description = db.Column(db.Text, nullable=False)
    amount = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    billing_periodicity = db.Column(db.String(30))
    competence_rule = db.Column(db.String(60))
    due_rule = db.Column(db.String(60))
    trigger_type = db.Column(db.String(40))
    trigger_reference_date = db.Column(db.String(40))
    is_recurring = db.Column(db.Boolean, nullable=False, default=True)
    order_index = db.Column(db.Integer, nullable=False, default=0)
    metadata_json = db.Column(JSONB, nullable=False, default=dict)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    contract_item = db.relationship("ContractItem", foreign_keys=[contract_item_id])

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "contract_id": self.contract_id,
            "contract_item_id": self.contract_item_id,
            "billing_code": self.billing_code,
            "description": self.description,
            "amount": float(self.amount or 0),
            "billing_periodicity": self.billing_periodicity,
            "competence_rule": self.competence_rule,
            "due_rule": self.due_rule,
            "trigger_type": self.trigger_type,
            "trigger_reference_date": self.trigger_reference_date,
            "is_recurring": bool(self.is_recurring),
            "order_index": self.order_index,
            "metadata_json": self.metadata_json or {},
        }


class ContractFinancialTerm(db.Model):
    __tablename__ = "contract_financial_terms"
    __table_args__ = (
        db.UniqueConstraint("contract_id", name="uq_contract_financial_terms_contract_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    contract_id = db.Column(db.Integer, db.ForeignKey("contracts.id"), nullable=False, index=True)
    default_bank_account_id = db.Column(db.Integer, db.ForeignKey("financial_bank_accounts.id"), index=True)
    default_payment_method_id = db.Column(db.Integer, db.ForeignKey("financial_payment_methods.id"), index=True)
    correction_index_id = db.Column(db.Integer, db.ForeignKey("financial_correction_indexes.id"), index=True)
    payment_term_type = db.Column(db.String(40))
    payment_term_days = db.Column(db.Integer)
    billing_method = db.Column(db.String(40))
    pricing_model = db.Column(db.String(40))
    adjustment_rule = db.Column(db.String(60))
    notes = db.Column(db.Text)
    metadata_json = db.Column(JSONB, nullable=False, default=dict)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "contract_id": self.contract_id,
            "default_bank_account_id": self.default_bank_account_id,
            "default_payment_method_id": self.default_payment_method_id,
            "correction_index_id": self.correction_index_id,
            "payment_term_type": self.payment_term_type,
            "payment_term_days": self.payment_term_days,
            "billing_method": self.billing_method,
            "pricing_model": self.pricing_model,
            "adjustment_rule": self.adjustment_rule,
            "notes": self.notes,
            "metadata_json": self.metadata_json or {},
        }


class ContractFiscalTerm(db.Model):
    __tablename__ = "contract_fiscal_terms"
    __table_args__ = (
        db.UniqueConstraint("contract_id", name="uq_contract_fiscal_terms_contract_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    contract_id = db.Column(db.Integer, db.ForeignKey("contracts.id"), nullable=False, index=True)
    fiscal_profile_code = db.Column(db.String(40))
    service_city = db.Column(db.String(120))
    tax_nature = db.Column(db.String(120))
    tax_observation = db.Column(db.Text)
    notes = db.Column(db.Text)
    metadata_json = db.Column(JSONB, nullable=False, default=dict)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "contract_id": self.contract_id,
            "fiscal_profile_code": self.fiscal_profile_code,
            "service_city": self.service_city,
            "tax_nature": self.tax_nature,
            "tax_observation": self.tax_observation,
            "notes": self.notes,
            "metadata_json": self.metadata_json or {},
        }


class ContractRetention(db.Model):
    __tablename__ = "contract_retentions"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    contract_id = db.Column(db.Integer, db.ForeignKey("contracts.id"), nullable=False, index=True)
    retention_type = db.Column(db.String(40), nullable=False)
    calculation_mode = db.Column(db.String(20))
    rate_percent = db.Column(db.Numeric(10, 4))
    fixed_amount = db.Column(db.Numeric(14, 2))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "contract_id": self.contract_id,
            "retention_type": self.retention_type,
            "calculation_mode": self.calculation_mode,
            "rate_percent": float(self.rate_percent or 0),
            "fixed_amount": float(self.fixed_amount or 0),
            "notes": self.notes,
        }


class ContractTrigger(db.Model):
    __tablename__ = "contract_triggers"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    contract_id = db.Column(db.Integer, db.ForeignKey("contracts.id"), nullable=False, index=True)
    trigger_type = db.Column(db.String(40), nullable=False)
    reference_date_type = db.Column(db.String(40))
    reference_date_value = db.Column(db.Date)
    offset_days = db.Column(db.Integer)
    periodicity = db.Column(db.String(30))
    alert_before_days = db.Column(db.Integer)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    metadata_json = db.Column(JSONB, nullable=False, default=dict)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "contract_id": self.contract_id,
            "trigger_type": self.trigger_type,
            "reference_date_type": self.reference_date_type,
            "reference_date_value": self.reference_date_value.isoformat() if self.reference_date_value else None,
            "offset_days": self.offset_days,
            "periodicity": self.periodicity,
            "alert_before_days": self.alert_before_days,
            "is_active": bool(self.is_active),
            "metadata_json": self.metadata_json or {},
        }


class ContractDocument(db.Model):
    __tablename__ = "contract_documents"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    contract_id = db.Column(db.Integer, db.ForeignKey("contracts.id"), nullable=False, index=True)
    document_type = db.Column(db.String(40), nullable=False)
    file_name = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    mime_type = db.Column(db.String(120))
    document_version = db.Column(db.String(30))
    source = db.Column(db.String(30), nullable=False, default="manual")
    is_signed_version = db.Column(db.Boolean, nullable=False, default=False)
    uploaded_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    metadata_json = db.Column(JSONB, nullable=False, default=dict)

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "contract_id": self.contract_id,
            "document_type": self.document_type,
            "file_name": self.file_name,
            "file_path": self.file_path,
            "mime_type": self.mime_type,
            "document_version": self.document_version,
            "source": self.source,
            "is_signed_version": bool(self.is_signed_version),
            "uploaded_by_user_id": self.uploaded_by_user_id,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None,
            "metadata_json": self.metadata_json or {},
        }
