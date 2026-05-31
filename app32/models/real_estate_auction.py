from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy.dialects.postgresql import JSONB

from . import db


REAL_ESTATE_AUCTION_STATUS_VALUES = (
    "draft",
    "in_analysis",
    "awaiting_auction",
    "won",
    "lost",
    "discarded",
    "available_for_sale",
    "sold",
)
REAL_ESTATE_AUCTION_TRIAGE_STATUS_VALUES = (
    "pending",
    "awaiting_auction",
    "auction_won",
    "auction_lost",
    "discarded",
)
REAL_ESTATE_AUCTION_ATTACHMENT_CATEGORY_VALUES = (
    "photo",
    "notice",
    "registry",
    "report",
    "other",
)
REAL_ESTATE_AUCTION_IMPORT_STATUS_VALUES = (
    "pending",
    "running",
    "imported",
    "duplicated",
    "error",
    "completed",
    "cancelled",
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


class RealEstateAuctionProperty(db.Model):
    __tablename__ = "real_estate_auction_properties"
    __table_args__ = (
        db.UniqueConstraint("company_id", "code", name="uq_re_auction_properties_company_code"),
        db.UniqueConstraint("company_id", "id", name="uq_re_auction_properties_company_id"),
        db.CheckConstraint(
            f"status IN {REAL_ESTATE_AUCTION_STATUS_VALUES}",
            name="ck_re_auction_properties_status",
        ),
        db.CheckConstraint(
            f"triage_status IN {REAL_ESTATE_AUCTION_TRIAGE_STATUS_VALUES}",
            name="ck_re_auction_properties_triage_status",
        ),
        db.Index("ix_re_auction_properties_company_status", "company_id", "status"),
        db.Index("ix_re_auction_properties_company_triage", "company_id", "triage_status"),
        db.Index("ix_re_auction_properties_company_city_state", "company_id", "city", "state"),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    code = db.Column(db.String(50), nullable=False)
    nickname = db.Column(db.String(255))
    address = db.Column(db.String(255), nullable=False)
    district = db.Column(db.String(120))
    city = db.Column(db.String(120), index=True)
    state = db.Column(db.String(2), index=True)
    zip_code = db.Column(db.String(20))
    property_type = db.Column(db.String(80))
    auxiliary_filter = db.Column(db.String(10), index=True)
    sale_modality = db.Column(db.String(120))
    land_area = db.Column(db.Numeric(14, 2))
    private_area = db.Column(db.Numeric(14, 2))
    built_area = db.Column(db.Numeric(14, 2))
    registry_number = db.Column(db.String(120))
    registry_office = db.Column(db.String(120))
    court_district = db.Column(db.String(120))
    bank = db.Column(db.String(120), index=True)
    occupied = db.Column(db.Boolean, nullable=False, default=True, index=True)
    status = db.Column(db.String(40), nullable=False, default="in_analysis", index=True)
    triage_status = db.Column(db.String(40), nullable=False, default="pending", index=True)
    triage_reason_code = db.Column(db.String(80))
    triage_reason_label = db.Column(db.String(160))
    triage_notes = db.Column(db.Text)
    appraisal_value = db.Column(db.Numeric(14, 2))
    estimated_quick_sale_value = db.Column(db.Numeric(14, 2))
    estimated_normal_sale_value = db.Column(db.Numeric(14, 2))
    recommended_max_bid = db.Column(db.Numeric(14, 2))
    auctioneer = db.Column(db.String(120))
    auction_url = db.Column(db.Text)
    notice_url = db.Column(db.Text)
    buyer_name = db.Column(db.String(255))
    broker_name = db.Column(db.String(255))
    closed_sale_value = db.Column(db.Numeric(14, 2))
    auction_won_at = db.Column(db.DateTime)
    available_for_sale_at = db.Column(db.DateTime)
    sold_at = db.Column(db.DateTime)
    metadata_json = db.Column(JSONB, nullable=False, default=dict)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)
    updated_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = db.Column(db.DateTime)

    company = db.relationship("Company", foreign_keys=[company_id])
    events = db.relationship(
        "RealEstateAuctionEvent",
        backref="property",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    financial_sheet = db.relationship(
        "RealEstateAuctionFinancialSheet",
        backref="property",
        uselist=False,
        cascade="all, delete-orphan",
    )
    due_diligence = db.relationship(
        "RealEstateAuctionDueDiligence",
        backref="property",
        uselist=False,
        cascade="all, delete-orphan",
    )
    attachments = db.relationship(
        "RealEstateAuctionAttachment",
        backref="property",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "code": self.code,
            "nickname": self.nickname,
            "address": self.address,
            "district": self.district,
            "city": self.city,
            "state": self.state,
            "zip_code": self.zip_code,
            "property_type": self.property_type,
            "auxiliary_filter": self.auxiliary_filter,
            "sale_modality": self.sale_modality,
            "land_area": _decimal(self.land_area),
            "private_area": _decimal(self.private_area),
            "built_area": _decimal(self.built_area),
            "registry_number": self.registry_number,
            "registry_office": self.registry_office,
            "court_district": self.court_district,
            "bank": self.bank,
            "occupied": bool(self.occupied),
            "status": self.status,
            "triage_status": self.triage_status,
            "triage_reason_code": self.triage_reason_code,
            "triage_reason_label": self.triage_reason_label,
            "triage_notes": self.triage_notes,
            "appraisal_value": _decimal(self.appraisal_value),
            "estimated_quick_sale_value": _decimal(self.estimated_quick_sale_value),
            "estimated_normal_sale_value": _decimal(self.estimated_normal_sale_value),
            "recommended_max_bid": _decimal(self.recommended_max_bid),
            "auctioneer": self.auctioneer,
            "auction_url": self.auction_url,
            "notice_url": self.notice_url,
            "buyer_name": self.buyer_name,
            "broker_name": self.broker_name,
            "closed_sale_value": _decimal(self.closed_sale_value),
            "auction_won_at": _iso(self.auction_won_at),
            "available_for_sale_at": _iso(self.available_for_sale_at),
            "sold_at": _iso(self.sold_at),
            "metadata_json": self.metadata_json or {},
            "created_at": _iso(self.created_at),
            "updated_at": _iso(self.updated_at),
        }


class RealEstateAuctionEvent(db.Model):
    __tablename__ = "real_estate_auction_events"
    __table_args__ = (
        db.ForeignKeyConstraint(
            ["company_id", "property_id"],
            ["real_estate_auction_properties.company_id", "real_estate_auction_properties.id"],
            ondelete="CASCADE",
            name="fk_re_auction_events_company_property",
        ),
        db.Index("ix_re_auction_events_company_datetime", "company_id", "auction_datetime"),
        db.Index("ix_re_auction_events_company_property", "company_id", "property_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    property_id = db.Column(db.Integer, nullable=False, index=True)
    auction_type = db.Column(db.String(40))
    auction_datetime = db.Column(db.DateTime, index=True)
    minimum_bid = db.Column(db.Numeric(14, 2))
    modality = db.Column(db.String(120))
    auctioneer = db.Column(db.String(120))
    winning_bid = db.Column(db.Numeric(14, 2))
    result = db.Column(db.String(60), nullable=False, default="pending", index=True)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "property_id": self.property_id,
            "auction_type": self.auction_type,
            "auction_datetime": _iso(self.auction_datetime),
            "minimum_bid": _decimal(self.minimum_bid),
            "modality": self.modality,
            "auctioneer": self.auctioneer,
            "winning_bid": _decimal(self.winning_bid),
            "result": self.result,
            "notes": self.notes,
            "created_at": _iso(self.created_at),
            "updated_at": _iso(self.updated_at),
        }


class RealEstateAuctionFinancialSheet(db.Model):
    __tablename__ = "real_estate_auction_financial_sheets"
    __table_args__ = (
        db.UniqueConstraint("company_id", "property_id", name="uq_re_auction_financial_sheets_company_property"),
        db.ForeignKeyConstraint(
            ["company_id", "property_id"],
            ["real_estate_auction_properties.company_id", "real_estate_auction_properties.id"],
            ondelete="CASCADE",
            name="fk_re_auction_financial_sheets_company_property",
        ),
        db.Index("ix_re_auction_financial_sheets_company_property", "company_id", "property_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    property_id = db.Column(db.Integer, nullable=False, index=True)
    winning_bid = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    auctioneer_commission_percent = db.Column(db.Numeric(7, 4), nullable=False, default=5)
    other_acquisition_costs = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    transfer_tax_percent = db.Column(db.Numeric(7, 4), nullable=False, default=0)
    transfer_tax_value = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    registry_cost_percent = db.Column(db.Numeric(7, 4), nullable=False, default=0)
    registry_cost_value = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    eviction_cost = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    renovation_budget = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    cleaning_cost = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    overdue_property_tax = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    future_property_tax = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    overdue_condo_fee = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    future_condo_fee = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    legal_fees = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    contingency_value = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    capital_cost_months = db.Column(db.Integer, nullable=False, default=0)
    capital_cost_percent = db.Column(db.Numeric(7, 4), nullable=False, default=0)
    minimum_profit_percent = db.Column(db.Numeric(7, 4), nullable=False, default=0)
    minimum_profit_value = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    projected_sale_value = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    broker_commission_percent = db.Column(db.Numeric(7, 4), nullable=False, default=5)
    sale_tax_percent = db.Column(db.Numeric(7, 4), nullable=False, default=0)
    operational_expenses = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    last_calculation_snapshot_json = db.Column(JSONB, nullable=False, default=dict)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "property_id": self.property_id,
            "winning_bid": _decimal(self.winning_bid),
            "auctioneer_commission_percent": _decimal(self.auctioneer_commission_percent),
            "other_acquisition_costs": _decimal(self.other_acquisition_costs),
            "transfer_tax_percent": _decimal(self.transfer_tax_percent),
            "transfer_tax_value": _decimal(self.transfer_tax_value),
            "registry_cost_percent": _decimal(self.registry_cost_percent),
            "registry_cost_value": _decimal(self.registry_cost_value),
            "eviction_cost": _decimal(self.eviction_cost),
            "renovation_budget": _decimal(self.renovation_budget),
            "cleaning_cost": _decimal(self.cleaning_cost),
            "overdue_property_tax": _decimal(self.overdue_property_tax),
            "future_property_tax": _decimal(self.future_property_tax),
            "overdue_condo_fee": _decimal(self.overdue_condo_fee),
            "future_condo_fee": _decimal(self.future_condo_fee),
            "legal_fees": _decimal(self.legal_fees),
            "contingency_value": _decimal(self.contingency_value),
            "capital_cost_months": self.capital_cost_months,
            "capital_cost_percent": _decimal(self.capital_cost_percent),
            "minimum_profit_percent": _decimal(self.minimum_profit_percent),
            "minimum_profit_value": _decimal(self.minimum_profit_value),
            "projected_sale_value": _decimal(self.projected_sale_value),
            "broker_commission_percent": _decimal(self.broker_commission_percent),
            "sale_tax_percent": _decimal(self.sale_tax_percent),
            "operational_expenses": _decimal(self.operational_expenses),
            "last_calculation_snapshot_json": self.last_calculation_snapshot_json or {},
            "created_at": _iso(self.created_at),
            "updated_at": _iso(self.updated_at),
        }


class RealEstateAuctionDueDiligence(db.Model):
    __tablename__ = "real_estate_auction_due_diligence"
    __table_args__ = (
        db.UniqueConstraint("company_id", "property_id", name="uq_re_auction_due_diligence_company_property"),
        db.ForeignKeyConstraint(
            ["company_id", "property_id"],
            ["real_estate_auction_properties.company_id", "real_estate_auction_properties.id"],
            ondelete="CASCADE",
            name="fk_re_auction_due_diligence_company_property",
        ),
        db.Index("ix_re_auction_due_diligence_company_property", "company_id", "property_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    property_id = db.Column(db.Integer, nullable=False, index=True)
    condo_fee_value = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    building_age = db.Column(db.Integer)
    building_description = db.Column(db.Text)
    property_description = db.Column(db.Text)
    region_square_meter_value = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    resident_contacted = db.Column(db.Boolean, nullable=False, default=False)
    resident_report = db.Column(db.Text)
    manager_contacted = db.Column(db.Boolean, nullable=False, default=False)
    manager_report = db.Column(db.Text)
    other_debts = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    internal_notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "property_id": self.property_id,
            "condo_fee_value": _decimal(self.condo_fee_value),
            "building_age": self.building_age,
            "building_description": self.building_description,
            "property_description": self.property_description,
            "region_square_meter_value": _decimal(self.region_square_meter_value),
            "resident_contacted": bool(self.resident_contacted),
            "resident_report": self.resident_report,
            "manager_contacted": bool(self.manager_contacted),
            "manager_report": self.manager_report,
            "other_debts": _decimal(self.other_debts),
            "internal_notes": self.internal_notes,
            "created_at": _iso(self.created_at),
            "updated_at": _iso(self.updated_at),
        }


class RealEstateAuctionAttachment(db.Model):
    __tablename__ = "real_estate_auction_attachments"
    __table_args__ = (
        db.ForeignKeyConstraint(
            ["company_id", "property_id"],
            ["real_estate_auction_properties.company_id", "real_estate_auction_properties.id"],
            ondelete="CASCADE",
            name="fk_re_auction_attachments_company_property",
        ),
        db.CheckConstraint(
            f"category IN {REAL_ESTATE_AUCTION_ATTACHMENT_CATEGORY_VALUES}",
            name="ck_re_auction_attachments_category",
        ),
        db.Index("ix_re_auction_attachments_company_property", "company_id", "property_id"),
        db.Index("ix_re_auction_attachments_company_category", "company_id", "category"),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    property_id = db.Column(db.Integer, nullable=False, index=True)
    category = db.Column(db.String(30), nullable=False, default="other", index=True)
    original_filename = db.Column(db.String(255))
    stored_filename = db.Column(db.String(255))
    storage_path = db.Column(db.String(1024), nullable=False)
    mime_type = db.Column(db.String(255))
    size_bytes = db.Column(db.Integer, nullable=False, default=0)
    metadata_json = db.Column(JSONB, nullable=False, default=dict)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "property_id": self.property_id,
            "category": self.category,
            "original_filename": self.original_filename,
            "stored_filename": self.stored_filename,
            "storage_path": self.storage_path,
            "mime_type": self.mime_type,
            "size_bytes": self.size_bytes,
            "metadata_json": self.metadata_json or {},
            "created_at": _iso(self.created_at),
            "updated_at": _iso(self.updated_at),
        }


class RealEstateAuctionSource(db.Model):
    __tablename__ = "real_estate_auction_sources"
    __table_args__ = (
        db.UniqueConstraint("company_id", "base_url", name="uq_re_auction_sources_company_base_url"),
        db.UniqueConstraint("company_id", "id", name="uq_re_auction_sources_company_id"),
        db.Index("ix_re_auction_sources_company_active", "company_id", "active"),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    name = db.Column(db.String(160), nullable=False)
    domain = db.Column(db.String(255), nullable=False, index=True)
    base_url = db.Column(db.String(1024), nullable=False)
    link_pattern = db.Column(db.String(255))
    listing_selector = db.Column(db.String(255))
    active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    metadata_json = db.Column(JSONB, nullable=False, default=dict)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    jobs = db.relationship(
        "RealEstateAuctionImportJob",
        backref="source",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "name": self.name,
            "domain": self.domain,
            "base_url": self.base_url,
            "link_pattern": self.link_pattern,
            "listing_selector": self.listing_selector,
            "active": bool(self.active),
            "metadata_json": self.metadata_json or {},
            "created_at": _iso(self.created_at),
            "updated_at": _iso(self.updated_at),
        }


class RealEstateAuctionImportJob(db.Model):
    __tablename__ = "real_estate_auction_import_jobs"
    __table_args__ = (
        db.UniqueConstraint("company_id", "id", name="uq_re_auction_import_jobs_company_id"),
        db.ForeignKeyConstraint(
            ["company_id", "source_id"],
            ["real_estate_auction_sources.company_id", "real_estate_auction_sources.id"],
            ondelete="CASCADE",
            name="fk_re_auction_import_jobs_company_source",
        ),
        db.CheckConstraint(
            f"status IN {REAL_ESTATE_AUCTION_IMPORT_STATUS_VALUES}",
            name="ck_re_auction_import_jobs_status",
        ),
        db.Index("ix_re_auction_import_jobs_company_status", "company_id", "status"),
        db.Index("ix_re_auction_import_jobs_company_source", "company_id", "source_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    source_id = db.Column(db.Integer, nullable=False, index=True)
    status = db.Column(db.String(30), nullable=False, default="pending", index=True)
    started_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    finished_at = db.Column(db.DateTime)
    total_found = db.Column(db.Integer, nullable=False, default=0)
    total_imported = db.Column(db.Integer, nullable=False, default=0)
    total_duplicated = db.Column(db.Integer, nullable=False, default=0)
    total_error = db.Column(db.Integer, nullable=False, default=0)
    notes = db.Column(db.Text)
    metadata_json = db.Column(JSONB, nullable=False, default=dict)

    items = db.relationship(
        "RealEstateAuctionImportJobItem",
        backref="job",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "source_id": self.source_id,
            "status": self.status,
            "started_at": _iso(self.started_at),
            "finished_at": _iso(self.finished_at),
            "total_found": self.total_found,
            "total_imported": self.total_imported,
            "total_duplicated": self.total_duplicated,
            "total_error": self.total_error,
            "notes": self.notes,
            "metadata_json": self.metadata_json or {},
        }


class RealEstateAuctionImportJobItem(db.Model):
    __tablename__ = "real_estate_auction_import_job_items"
    __table_args__ = (
        db.UniqueConstraint("company_id", "job_id", "fingerprint", name="uq_re_auction_import_items_company_job_fp"),
        db.ForeignKeyConstraint(
            ["company_id", "job_id"],
            ["real_estate_auction_import_jobs.company_id", "real_estate_auction_import_jobs.id"],
            ondelete="CASCADE",
            name="fk_re_auction_import_items_company_job",
        ),
        db.CheckConstraint(
            f"status IN {REAL_ESTATE_AUCTION_IMPORT_STATUS_VALUES}",
            name="ck_re_auction_import_items_status",
        ),
        db.Index("ix_re_auction_import_items_company_job", "company_id", "job_id"),
        db.Index("ix_re_auction_import_items_company_status", "company_id", "status"),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    job_id = db.Column(db.Integer, nullable=False, index=True)
    url = db.Column(db.String(1024), nullable=False)
    status = db.Column(db.String(30), nullable=False, default="pending", index=True)
    error_message = db.Column(db.Text)
    fingerprint = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "job_id": self.job_id,
            "url": self.url,
            "status": self.status,
            "error_message": self.error_message,
            "fingerprint": self.fingerprint,
            "created_at": _iso(self.created_at),
            "updated_at": _iso(self.updated_at),
        }


class RealEstateAuctionTenantSettings(db.Model):
    __tablename__ = "real_estate_auction_tenant_settings"
    __table_args__ = (
        db.UniqueConstraint("company_id", name="uq_re_auction_tenant_settings_company"),
        db.Index("ix_re_auction_tenant_settings_enabled", "company_id", "module_enabled"),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    module_enabled = db.Column(db.Boolean, nullable=False, default=False, index=True)
    display_name = db.Column(db.String(160), nullable=False, default="Leilões Imobiliários")
    code_prefix = db.Column(db.String(20))
    settings_json = db.Column(JSONB, nullable=False, default=dict)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    company = db.relationship("Company", foreign_keys=[company_id])

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "module_enabled": bool(self.module_enabled),
            "display_name": self.display_name,
            "code_prefix": self.code_prefix,
            "settings_json": self.settings_json or {},
            "created_at": _iso(self.created_at),
            "updated_at": _iso(self.updated_at),
        }
