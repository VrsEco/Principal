from __future__ import annotations

from datetime import datetime

from sqlalchemy.dialects.postgresql import JSONB

from . import db


FINANCIAL_AUTOMATION_STATUS_VALUES = (
    "imported",
    "validated",
    "generated",
    "excluded",
)

FINANCIAL_AUTOMATION_ORIGIN_VALUES = (
    "accountability",
    "csv",
    "xlsx",
    "ofx",
    "api",
    "mcp",
    "manual_upload",
    "integration",
)

FINANCIAL_AUTOMATION_ENTRY_DIRECTION_VALUES = (
    "payable",
    "receivable",
)

FINANCIAL_AUTOMATION_SETTLEMENT_STATE_VALUES = (
    "settled",
    "open",
)

FINANCIAL_AUTOMATION_DOMAIN_TYPE_VALUES = (
    "project",
    "process",
)

FINANCIAL_AUTOMATION_DOCUMENT_FAMILY_VALUES = (
    "fiscal",
    "receipt",
    "bank",
    "generic",
)

FINANCIAL_AUTOMATION_DOCUMENT_TYPE_VALUES = (
    "nfe_xml",
    "nfce_xml",
    "cte_xml",
    "danfe_pdf",
    "dacte_pdf",
    "receipt_pdf",
    "receipt_image",
    "spreadsheet",
    "ofx",
    "unknown_document",
)

FINANCIAL_AUTOMATION_SOURCE_KIND_VALUES = (
    "xml",
    "pdf",
    "image",
    "spreadsheet",
    "ofx",
    "text",
    "binary",
)

FINANCIAL_AUTOMATION_PARSER_STATUS_VALUES = (
    "uploaded",
    "parsed",
    "grouped",
    "needs_review",
    "failed",
)


class FinancialAutomationBatch(db.Model):
    __tablename__ = "financial_automation_batches"
    __table_args__ = (
        db.Index("ix_financial_automation_batches_company_origin_created", "company_id", "origin_type", "created_at"),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    origin_type = db.Column(db.String(50), nullable=False, index=True)
    source_label = db.Column(db.String(255))
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)
    status_summary_json = db.Column(JSONB, nullable=False, default=dict)
    metadata_json = db.Column(JSONB, nullable=False, default=dict)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = db.Column(db.DateTime)

    documents = db.relationship("FinancialAutomationDocument", backref="batch", lazy="dynamic")
    records = db.relationship("FinancialAutomationRecord", backref="batch", lazy="dynamic")

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "origin_type": self.origin_type,
            "source_label": self.source_label,
            "created_by_user_id": self.created_by_user_id,
            "status_summary_json": self.status_summary_json or {},
            "metadata_json": self.metadata_json or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
        }


class FinancialAutomationDocument(db.Model):
    __tablename__ = "financial_automation_documents"
    __table_args__ = (
        db.Index("ix_financial_automation_documents_company_batch", "company_id", "batch_id"),
        db.Index("ix_financial_automation_documents_company_group", "company_id", "document_group_key"),
        db.Index("ix_financial_automation_documents_company_type", "company_id", "document_type"),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    batch_id = db.Column(db.Integer, db.ForeignKey("financial_automation_batches.id"), nullable=False, index=True)
    file_name = db.Column(db.String(255), nullable=False)
    stored_relative_path = db.Column(db.String(500))
    original_relative_path = db.Column(db.String(500))
    optimized_relative_path = db.Column(db.String(500))
    preview_relative_path = db.Column(db.String(500))
    mime_type = db.Column(db.String(120))
    file_size = db.Column(db.Integer)
    file_size_original = db.Column(db.Integer)
    file_size_optimized = db.Column(db.Integer)
    sha256 = db.Column(db.String(64))
    document_family = db.Column(db.String(30), index=True)
    document_type = db.Column(db.String(50), index=True)
    source_kind = db.Column(db.String(30), index=True)
    parser_status = db.Column(db.String(30), nullable=False, default="uploaded", index=True)
    parser_version = db.Column(db.String(30))
    document_group_key = db.Column(db.String(255), index=True)
    confidence_score = db.Column(db.Numeric(5, 4))
    extracted_text = db.Column(db.Text)
    preview_payload_json = db.Column(JSONB, nullable=False, default=dict)
    structured_payload_json = db.Column(JSONB, nullable=False, default=dict)
    metadata_json = db.Column(JSONB, nullable=False, default=dict)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = db.Column(db.DateTime)

    records = db.relationship("FinancialAutomationRecord", backref="source_document", lazy="dynamic")

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "batch_id": self.batch_id,
            "file_name": self.file_name,
            "stored_relative_path": self.stored_relative_path,
            "original_relative_path": self.original_relative_path,
            "optimized_relative_path": self.optimized_relative_path,
            "preview_relative_path": self.preview_relative_path,
            "mime_type": self.mime_type,
            "file_size": self.file_size,
            "file_size_original": self.file_size_original,
            "file_size_optimized": self.file_size_optimized,
            "sha256": self.sha256,
            "document_family": self.document_family,
            "document_type": self.document_type,
            "source_kind": self.source_kind,
            "parser_status": self.parser_status,
            "parser_version": self.parser_version,
            "document_group_key": self.document_group_key,
            "confidence_score": float(self.confidence_score) if self.confidence_score is not None else None,
            "extracted_text": self.extracted_text,
            "preview_payload_json": self.preview_payload_json or {},
            "structured_payload_json": self.structured_payload_json or {},
            "metadata_json": self.metadata_json or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
        }


class FinancialAutomationRecord(db.Model):
    __tablename__ = "financial_automation_records"
    __table_args__ = (
        db.Index("ix_financial_automation_records_company_status", "company_id", "status"),
        db.Index("ix_financial_automation_records_company_batch", "company_id", "batch_id"),
        db.Index("ix_financial_automation_records_generated_entry", "generated_financial_entry_id"),
        db.Index("ix_financial_automation_records_generated_schedule", "generated_financial_schedule_id"),
        db.Index("ix_financial_automation_records_company_group", "company_id", "document_group_key"),
        db.Index("ix_financial_automation_records_company_document_key", "company_id", "document_key"),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    batch_id = db.Column(db.Integer, db.ForeignKey("financial_automation_batches.id"), nullable=False, index=True)
    source_document_id = db.Column(db.Integer, db.ForeignKey("financial_automation_documents.id"), index=True)
    status = db.Column(db.String(20), nullable=False, default="imported", index=True)
    entry_direction = db.Column(db.String(20), nullable=False, index=True)
    settlement_state = db.Column(db.String(20), nullable=False, default="open", index=True)
    description = db.Column(db.String(255))
    counterparty_id = db.Column(db.Integer, db.ForeignKey("financial_counterparties.id"), index=True)
    bank_account_id = db.Column(db.Integer, db.ForeignKey("financial_bank_accounts.id"), index=True)
    chart_account_id = db.Column(db.Integer, db.ForeignKey("financial_chart_accounts.id"), index=True)
    cost_center_id = db.Column(db.Integer, db.ForeignKey("financial_cost_centers.id"), index=True)
    domain_type = db.Column(db.String(20), index=True)
    domain_source_id = db.Column(db.Integer, index=True)
    document_group_key = db.Column(db.String(255), index=True)
    document_type = db.Column(db.String(50), index=True)
    document_key = db.Column(db.String(64), index=True)
    external_document_number = db.Column(db.String(120), index=True)
    issuer_name = db.Column(db.String(255))
    issuer_document = db.Column(db.String(32), index=True)
    recipient_name = db.Column(db.String(255))
    recipient_document = db.Column(db.String(32), index=True)
    issue_date = db.Column(db.Date, index=True)
    amount = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    competence_date = db.Column(db.Date, index=True)
    due_date = db.Column(db.Date, index=True)
    settlement_date = db.Column(db.Date, index=True)
    confidence_score = db.Column(db.Numeric(5, 4))
    validation_notes = db.Column(db.Text)
    extracted_fields_json = db.Column(JSONB, nullable=False, default=dict)
    review_flags_json = db.Column(JSONB, nullable=False, default=list)
    normalized_payload_json = db.Column(JSONB, nullable=False, default=dict)
    metadata_json = db.Column(JSONB, nullable=False, default=dict)
    generated_financial_entry_id = db.Column(db.Integer, db.ForeignKey("financial_entries.id"), index=True)
    generated_financial_schedule_id = db.Column(db.Integer, db.ForeignKey("financial_schedules.id"), index=True)
    validated_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)
    validated_at = db.Column(db.DateTime)
    generated_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)
    generated_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = db.Column(db.DateTime)

    history_items = db.relationship("FinancialAutomationHistory", backref="record", lazy="dynamic")

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "batch_id": self.batch_id,
            "source_document_id": self.source_document_id,
            "status": self.status,
            "entry_direction": self.entry_direction,
            "settlement_state": self.settlement_state,
            "description": self.description,
            "counterparty_id": self.counterparty_id,
            "bank_account_id": self.bank_account_id,
            "chart_account_id": self.chart_account_id,
            "cost_center_id": self.cost_center_id,
            "domain_type": self.domain_type,
            "domain_source_id": self.domain_source_id,
            "document_group_key": self.document_group_key,
            "document_type": self.document_type,
            "document_key": self.document_key,
            "external_document_number": self.external_document_number,
            "issuer_name": self.issuer_name,
            "issuer_document": self.issuer_document,
            "recipient_name": self.recipient_name,
            "recipient_document": self.recipient_document,
            "issue_date": self.issue_date.isoformat() if self.issue_date else None,
            "amount": float(self.amount or 0),
            "competence_date": self.competence_date.isoformat() if self.competence_date else None,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "settlement_date": self.settlement_date.isoformat() if self.settlement_date else None,
            "confidence_score": float(self.confidence_score) if self.confidence_score is not None else None,
            "validation_notes": self.validation_notes,
            "extracted_fields_json": self.extracted_fields_json or {},
            "review_flags_json": self.review_flags_json or [],
            "normalized_payload_json": self.normalized_payload_json or {},
            "metadata_json": self.metadata_json or {},
            "generated_financial_entry_id": self.generated_financial_entry_id,
            "generated_financial_schedule_id": self.generated_financial_schedule_id,
            "validated_by_user_id": self.validated_by_user_id,
            "validated_at": self.validated_at.isoformat() if self.validated_at else None,
            "generated_by_user_id": self.generated_by_user_id,
            "generated_at": self.generated_at.isoformat() if self.generated_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
        }


class FinancialAutomationHistory(db.Model):
    __tablename__ = "financial_automation_history"
    __table_args__ = (
        db.Index("ix_financial_automation_history_company_record", "company_id", "record_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    record_id = db.Column(db.Integer, db.ForeignKey("financial_automation_records.id"), nullable=False, index=True)
    action_type = db.Column(db.String(50), nullable=False, index=True)
    performed_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)
    payload_before_json = db.Column(JSONB, nullable=False, default=dict)
    payload_after_json = db.Column(JSONB, nullable=False, default=dict)
    metadata_json = db.Column(JSONB, nullable=False, default=dict)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "record_id": self.record_id,
            "action_type": self.action_type,
            "performed_by_user_id": self.performed_by_user_id,
            "payload_before_json": self.payload_before_json or {},
            "payload_after_json": self.payload_after_json or {},
            "metadata_json": self.metadata_json or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
