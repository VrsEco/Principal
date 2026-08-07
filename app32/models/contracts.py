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
        metadata = self.metadata_json or {}
        zip_code = (
            metadata.get("zip_code")
            or metadata.get("Endereco_Cep")
            or metadata.get("endereco_cep")
            or metadata.get("cep")
        )
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
            "zip_code": zip_code,
            "address_line": metadata.get("address_line") or metadata.get("Endereco_Logradouro") or metadata.get("logradouro"),
            "address_number": metadata.get("address_number") or metadata.get("Endereco_Numero") or metadata.get("numero"),
            "complement": metadata.get("complement") or metadata.get("Endereco_Complemento") or metadata.get("complemento"),
            "district": metadata.get("district") or metadata.get("Endereco_Bairro") or metadata.get("bairro"),
            "city_name": metadata.get("city_name") or metadata.get("Endereco_Cidade_Nome") or metadata.get("cidade"),
            "city_code_ibge": metadata.get("city_code_ibge") or metadata.get("Endereco_Cidade_Codigo") or metadata.get("codigo_ibge"),
            "uf": metadata.get("uf") or metadata.get("Endereco_Estado") or metadata.get("estado"),
            "country_code": metadata.get("country_code") or metadata.get("Endereco_Pais") or metadata.get("pais") or "BRA",
            "is_customer": bool(self.is_customer),
            "is_supplier": bool(self.is_supplier),
            "status": self.status,
            "notes": self.notes,
            "metadata_json": metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ContractingLegalEntity(db.Model):
    __tablename__ = "contracting_legal_entities"
    __table_args__ = (
        db.UniqueConstraint("company_id", "code", name="uq_contracting_legal_entities_company_code"),
        db.UniqueConstraint("company_id", "cnpj", name="uq_contracting_legal_entities_company_cnpj"),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    code = db.Column(db.String(30), nullable=False)
    legal_name = db.Column(db.String(255), nullable=False)
    trade_name = db.Column(db.String(255))
    cnpj = db.Column(db.String(20), nullable=False, index=True)
    municipal_registration = db.Column(db.String(50))
    state_registration = db.Column(db.String(50))
    tax_regime = db.Column(db.String(50))
    cnae = db.Column(db.String(30))
    service_city = db.Column(db.String(120))
    city_code_ibge = db.Column(db.String(20))
    uf = db.Column(db.String(2))
    zip_code = db.Column(db.String(20))
    address_line = db.Column(db.String(255))
    address_number = db.Column(db.String(30))
    district = db.Column(db.String(120))
    complement = db.Column(db.String(120))
    email = db.Column(db.String(255))
    phone = db.Column(db.String(50))
    nfs_provider = db.Column(db.String(80))
    integration_mode = db.Column(db.String(30), nullable=False, default="manual")
    api_profile_id = db.Column(db.Integer)
    spreadsheet_profile_id = db.Column(db.Integer)
    metadata_json = db.Column(JSONB, nullable=False, default=dict)
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "code": self.code,
            "legal_name": self.legal_name,
            "trade_name": self.trade_name,
            "cnpj": self.cnpj,
            "municipal_registration": self.municipal_registration,
            "state_registration": self.state_registration,
            "tax_regime": self.tax_regime,
            "cnae": self.cnae,
            "service_city": self.service_city,
            "city_code_ibge": self.city_code_ibge,
            "uf": self.uf,
            "zip_code": self.zip_code,
            "address_line": self.address_line,
            "address_number": self.address_number,
            "district": self.district,
            "complement": self.complement,
            "email": self.email,
            "phone": self.phone,
            "nfs_provider": self.nfs_provider,
            "integration_mode": self.integration_mode,
            "api_profile_id": self.api_profile_id,
            "spreadsheet_profile_id": self.spreadsheet_profile_id,
            "metadata_json": self.metadata_json or {},
            "is_active": bool(self.is_active),
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
    contracting_legal_entity_id = db.Column(db.Integer, db.ForeignKey("contracting_legal_entities.id"), index=True)
    manager_employee_id = db.Column(db.Integer, db.ForeignKey("employees.id"), index=True)
    signed_at = db.Column(db.Date)
    service_start_at = db.Column(db.Date)
    service_end_at = db.Column(db.Date)
    billing_start_at = db.Column(db.Date)
    billing_end_at = db.Column(db.Date)
    last_billing_at = db.Column(db.Date)
    renewal_date = db.Column(db.Date)
    adjustment_date = db.Column(db.Date)
    termination_date = db.Column(db.Date)
    periodicity = db.Column(db.String(30))
    competence_rule = db.Column(db.String(60))
    due_rule = db.Column(db.String(60))
    renewal_rule = db.Column(db.String(60))
    end_reason = db.Column(db.String(40))
    previous_contract_id = db.Column(db.Integer, db.ForeignKey("contracts.id"), index=True)
    notes = db.Column(db.Text)
    version = db.Column(db.Integer, nullable=False, default=1)
    metadata_json = db.Column(JSONB, nullable=False, default=dict)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)
    updated_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = db.Column(db.DateTime)

    party = db.relationship("ContractParty", foreign_keys=[party_id])
    contracting_legal_entity = db.relationship("ContractingLegalEntity", foreign_keys=[contracting_legal_entity_id])
    manager_employee = db.relationship("Employee", foreign_keys=[manager_employee_id])
    previous_contract = db.relationship("Contract", remote_side=[id], foreign_keys=[previous_contract_id])
    items = db.relationship("ContractItem", backref="contract", lazy="dynamic", cascade="all, delete-orphan")
    billing_items = db.relationship("ContractBillingItem", backref="contract", lazy="dynamic", cascade="all, delete-orphan")
    retentions = db.relationship("ContractRetention", backref="contract", lazy="dynamic", cascade="all, delete-orphan")
    triggers = db.relationship("ContractTrigger", backref="contract", lazy="dynamic", cascade="all, delete-orphan")
    documents = db.relationship("ContractDocument", backref="contract", lazy="dynamic", cascade="all, delete-orphan")
    clauses = db.relationship("ContractClause", backref="contract", lazy="dynamic", cascade="all, delete-orphan")
    notes_log = db.relationship("ContractNote", backref="contract", lazy="dynamic", cascade="all, delete-orphan")
    events = db.relationship("ContractEvent", backref="contract", lazy="dynamic", cascade="all, delete-orphan")

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
            "contracting_legal_entity_id": self.contracting_legal_entity_id,
            "manager_employee_id": self.manager_employee_id,
            "signed_at": self.signed_at.isoformat() if self.signed_at else None,
            "service_start_at": self.service_start_at.isoformat() if self.service_start_at else None,
            "service_end_at": self.service_end_at.isoformat() if self.service_end_at else None,
            "billing_start_at": self.billing_start_at.isoformat() if self.billing_start_at else None,
            "billing_end_at": self.billing_end_at.isoformat() if self.billing_end_at else None,
            "last_billing_at": self.last_billing_at.isoformat() if self.last_billing_at else None,
            "renewal_date": self.renewal_date.isoformat() if self.renewal_date else None,
            "adjustment_date": self.adjustment_date.isoformat() if self.adjustment_date else None,
            "termination_date": self.termination_date.isoformat() if self.termination_date else None,
            "periodicity": self.periodicity,
            "competence_rule": self.competence_rule,
            "due_rule": self.due_rule,
            "renewal_rule": self.renewal_rule,
            "end_reason": self.end_reason,
            "previous_contract_id": self.previous_contract_id,
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


class ContractNativeBilling(db.Model):
    __tablename__ = "contract_native_billings"
    __table_args__ = (
        db.UniqueConstraint("company_id", "billing_code", name="uq_contract_native_billings_company_code"),
        db.UniqueConstraint("company_id", "idempotency_key", name="uq_contract_native_billings_company_idempotency"),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    contract_id = db.Column(db.Integer, db.ForeignKey("contracts.id"), nullable=False, index=True)
    party_id = db.Column(db.Integer, db.ForeignKey("contract_parties.id"), nullable=False, index=True)
    billing_code = db.Column(db.String(40), nullable=False)
    status = db.Column(db.String(30), nullable=False, default="generated", index=True)
    source_type = db.Column(db.String(30), nullable=False, default="native_contract")
    competence_start = db.Column(db.Date, nullable=False, index=True)
    competence_end = db.Column(db.Date, nullable=False, index=True)
    issue_date = db.Column(db.Date, nullable=False)
    due_date = db.Column(db.Date, index=True)
    gross_amount = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    net_amount = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    idempotency_key = db.Column(db.String(160), nullable=False)
    generated_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)
    metadata_json = db.Column(JSONB, nullable=False, default=dict)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    contract = db.relationship("Contract", foreign_keys=[contract_id], backref=db.backref("native_billings", lazy="dynamic", cascade="all, delete-orphan"))
    party = db.relationship("ContractParty", foreign_keys=[party_id])

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "contract_id": self.contract_id,
            "party_id": self.party_id,
            "billing_code": self.billing_code,
            "status": self.status,
            "source_type": self.source_type,
            "competence_start": self.competence_start.isoformat() if self.competence_start else None,
            "competence_end": self.competence_end.isoformat() if self.competence_end else None,
            "issue_date": self.issue_date.isoformat() if self.issue_date else None,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "gross_amount": float(self.gross_amount or 0),
            "net_amount": float(self.net_amount or 0),
            "idempotency_key": self.idempotency_key,
            "generated_by_user_id": self.generated_by_user_id,
            "metadata_json": self.metadata_json or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ContractNativeBillingItem(db.Model):
    __tablename__ = "contract_native_billing_items"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    contract_native_billing_id = db.Column(db.Integer, db.ForeignKey("contract_native_billings.id"), nullable=False, index=True)
    contract_billing_item_id = db.Column(db.Integer, db.ForeignKey("contract_billing_items.id"), index=True)
    contract_item_id = db.Column(db.Integer, db.ForeignKey("contract_items.id"), index=True)
    description = db.Column(db.Text, nullable=False)
    amount = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    competence_rule = db.Column(db.String(60))
    due_rule = db.Column(db.String(60))
    trigger_type = db.Column(db.String(40))
    trigger_reference_date = db.Column(db.String(40))
    metadata_json = db.Column(JSONB, nullable=False, default=dict)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    contract_native_billing = db.relationship(
        "ContractNativeBilling",
        foreign_keys=[contract_native_billing_id],
        backref=db.backref("items", lazy="dynamic", cascade="all, delete-orphan"),
    )
    contract_billing_item = db.relationship("ContractBillingItem", foreign_keys=[contract_billing_item_id])
    contract_item = db.relationship("ContractItem", foreign_keys=[contract_item_id])

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "contract_native_billing_id": self.contract_native_billing_id,
            "contract_billing_item_id": self.contract_billing_item_id,
            "contract_item_id": self.contract_item_id,
            "description": self.description,
            "amount": float(self.amount or 0),
            "competence_rule": self.competence_rule,
            "due_rule": self.due_rule,
            "trigger_type": self.trigger_type,
            "trigger_reference_date": self.trigger_reference_date,
            "metadata_json": self.metadata_json or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
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
    default_chart_account_id = db.Column(db.Integer, db.ForeignKey("financial_chart_accounts.id"), index=True)
    default_cost_center_id = db.Column(db.Integer, db.ForeignKey("financial_cost_centers.id"), index=True)
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
            "default_chart_account_id": self.default_chart_account_id,
            "default_cost_center_id": self.default_cost_center_id,
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
    contracting_legal_entity_id = db.Column(db.Integer, db.ForeignKey("contracting_legal_entities.id"), index=True)
    fiscal_profile_code = db.Column(db.String(40))
    integration_mode = db.Column(db.String(30))
    nfs_provider = db.Column(db.String(80))
    default_rps_series = db.Column(db.String(30))
    service_code = db.Column(db.String(60))
    service_list_item = db.Column(db.String(60))
    operation_nature = db.Column(db.String(120))
    service_city = db.Column(db.String(120))
    iss_city = db.Column(db.String(120))
    tax_nature = db.Column(db.String(120))
    api_profile_id = db.Column(db.Integer)
    spreadsheet_profile_id = db.Column(db.Integer)
    withholding_flags = db.Column(JSONB, nullable=False, default=dict)
    tax_observation = db.Column(db.Text)
    notes = db.Column(db.Text)
    metadata_json = db.Column(JSONB, nullable=False, default=dict)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    contracting_legal_entity = db.relationship("ContractingLegalEntity", foreign_keys=[contracting_legal_entity_id])

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "contract_id": self.contract_id,
            "contracting_legal_entity_id": self.contracting_legal_entity_id,
            "fiscal_profile_code": self.fiscal_profile_code,
            "integration_mode": self.integration_mode,
            "nfs_provider": self.nfs_provider,
            "default_rps_series": self.default_rps_series,
            "service_code": self.service_code,
            "service_list_item": self.service_list_item,
            "operation_nature": self.operation_nature,
            "service_city": self.service_city,
            "iss_city": self.iss_city,
            "tax_nature": self.tax_nature,
            "api_profile_id": self.api_profile_id,
            "spreadsheet_profile_id": self.spreadsheet_profile_id,
            "withholding_flags": self.withholding_flags or {},
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


class ContractClause(db.Model):
    __tablename__ = "contract_clauses"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    contract_id = db.Column(db.Integer, db.ForeignKey("contracts.id"), nullable=False, index=True)
    clause_type = db.Column(db.String(40))
    title = db.Column(db.String(255))
    content = db.Column(db.Text, nullable=False)
    order_index = db.Column(db.Integer, nullable=False, default=0)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)
    updated_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "contract_id": self.contract_id,
            "clause_type": self.clause_type,
            "title": self.title,
            "content": self.content,
            "order_index": self.order_index,
            "created_by_user_id": self.created_by_user_id,
            "updated_by_user_id": self.updated_by_user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ContractNote(db.Model):
    __tablename__ = "contract_notes"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    contract_id = db.Column(db.Integer, db.ForeignKey("contracts.id"), nullable=False, index=True)
    note_type = db.Column(db.String(40), nullable=False, default="general")
    note_text = db.Column(db.Text, nullable=False)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "contract_id": self.contract_id,
            "note_type": self.note_type,
            "note_text": self.note_text,
            "created_by_user_id": self.created_by_user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ContractEvent(db.Model):
    __tablename__ = "contract_events"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    contract_id = db.Column(db.Integer, db.ForeignKey("contracts.id"), nullable=False, index=True)
    event_type = db.Column(db.String(60), nullable=False, index=True)
    description = db.Column(db.Text)
    event_payload = db.Column(JSONB, nullable=False, default=dict)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "contract_id": self.contract_id,
            "event_type": self.event_type,
            "description": self.description,
            "event_payload": self.event_payload or {},
            "created_by_user_id": self.created_by_user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
