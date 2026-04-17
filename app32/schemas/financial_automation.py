from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from models.financial_automation import (
    FINANCIAL_AUTOMATION_DOCUMENT_FAMILY_VALUES,
    FINANCIAL_AUTOMATION_DOCUMENT_TYPE_VALUES,
    FINANCIAL_AUTOMATION_DOMAIN_TYPE_VALUES,
    FINANCIAL_AUTOMATION_ENTRY_DIRECTION_VALUES,
    FINANCIAL_AUTOMATION_ORIGIN_VALUES,
    FINANCIAL_AUTOMATION_PARSER_STATUS_VALUES,
    FINANCIAL_AUTOMATION_SOURCE_KIND_VALUES,
    FINANCIAL_AUTOMATION_SETTLEMENT_STATE_VALUES,
    FINANCIAL_AUTOMATION_STATUS_VALUES,
)


def _choices_pattern(values: tuple[str, ...]) -> str:
    return "^(" + "|".join(values) + ")$"


def _normalize_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


class FinancialAutomationBatchCreateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_id: int
    origin_type: str = Field(..., pattern=_choices_pattern(FINANCIAL_AUTOMATION_ORIGIN_VALUES))
    source_label: Optional[str] = Field(None, max_length=255)
    created_by_user_id: Optional[int] = None
    metadata_json: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("source_label", mode="before")
    @classmethod
    def normalize_source_label(cls, value):
        return _normalize_text(value)


class FinancialAutomationDocumentCreateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_id: int
    batch_id: int
    file_name: str = Field(..., min_length=1, max_length=255)
    stored_relative_path: Optional[str] = Field(None, max_length=500)
    original_relative_path: Optional[str] = Field(None, max_length=500)
    optimized_relative_path: Optional[str] = Field(None, max_length=500)
    preview_relative_path: Optional[str] = Field(None, max_length=500)
    mime_type: Optional[str] = Field(None, max_length=120)
    file_size: Optional[int] = Field(None, ge=0)
    file_size_original: Optional[int] = Field(None, ge=0)
    file_size_optimized: Optional[int] = Field(None, ge=0)
    sha256: Optional[str] = Field(None, max_length=64)
    document_family: Optional[str] = Field(None, pattern=_choices_pattern(FINANCIAL_AUTOMATION_DOCUMENT_FAMILY_VALUES))
    document_type: Optional[str] = Field(None, pattern=_choices_pattern(FINANCIAL_AUTOMATION_DOCUMENT_TYPE_VALUES))
    source_kind: Optional[str] = Field(None, pattern=_choices_pattern(FINANCIAL_AUTOMATION_SOURCE_KIND_VALUES))
    parser_status: Optional[str] = Field(None, pattern=_choices_pattern(FINANCIAL_AUTOMATION_PARSER_STATUS_VALUES))
    parser_version: Optional[str] = Field(None, max_length=30)
    document_group_key: Optional[str] = Field(None, max_length=255)
    confidence_score: Optional[Decimal] = Field(None, ge=0, le=1)
    extracted_text: Optional[str] = None
    preview_payload_json: Dict[str, Any] = Field(default_factory=dict)
    structured_payload_json: Dict[str, Any] = Field(default_factory=dict)
    metadata_json: Dict[str, Any] = Field(default_factory=dict)

    @field_validator(
        "file_name",
        "stored_relative_path",
        "original_relative_path",
        "optimized_relative_path",
        "preview_relative_path",
        "mime_type",
        "document_family",
        "document_type",
        "source_kind",
        "parser_status",
        "parser_version",
        "document_group_key",
        mode="before",
    )
    @classmethod
    def normalize_text_fields(cls, value):
        return _normalize_text(value)


class FinancialAutomationRecordCreateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_id: int
    batch_id: int
    source_document_id: Optional[int] = None
    status: str = Field("imported", pattern=_choices_pattern(FINANCIAL_AUTOMATION_STATUS_VALUES))
    entry_direction: str = Field(..., pattern=_choices_pattern(FINANCIAL_AUTOMATION_ENTRY_DIRECTION_VALUES))
    settlement_state: str = Field("open", pattern=_choices_pattern(FINANCIAL_AUTOMATION_SETTLEMENT_STATE_VALUES))
    description: Optional[str] = Field(None, max_length=255)
    counterparty_id: Optional[int] = None
    bank_account_id: Optional[int] = None
    chart_account_id: Optional[int] = None
    cost_center_id: Optional[int] = None
    domain_type: Optional[str] = Field(None, pattern=_choices_pattern(FINANCIAL_AUTOMATION_DOMAIN_TYPE_VALUES))
    domain_source_id: Optional[int] = None
    document_group_key: Optional[str] = Field(None, max_length=255)
    document_type: Optional[str] = Field(None, pattern=_choices_pattern(FINANCIAL_AUTOMATION_DOCUMENT_TYPE_VALUES))
    document_key: Optional[str] = Field(None, max_length=64)
    external_document_number: Optional[str] = Field(None, max_length=120)
    issuer_name: Optional[str] = Field(None, max_length=255)
    issuer_document: Optional[str] = Field(None, max_length=32)
    recipient_name: Optional[str] = Field(None, max_length=255)
    recipient_document: Optional[str] = Field(None, max_length=32)
    issue_date: Optional[date] = None
    amount: Decimal = Field(..., ge=0)
    competence_date: Optional[date] = None
    due_date: Optional[date] = None
    confidence_score: Optional[Decimal] = Field(None, ge=0, le=1)
    validation_notes: Optional[str] = None
    extracted_fields_json: Dict[str, Any] = Field(default_factory=dict)
    review_flags_json: List[str] = Field(default_factory=list)
    normalized_payload_json: Dict[str, Any] = Field(default_factory=dict)
    metadata_json: Dict[str, Any] = Field(default_factory=dict)

    @field_validator(
        "description",
        "validation_notes",
        "document_group_key",
        "document_type",
        "document_key",
        "external_document_number",
        "issuer_name",
        "issuer_document",
        "recipient_name",
        "recipient_document",
        mode="before",
    )
    @classmethod
    def normalize_text_fields(cls, value):
        return _normalize_text(value)


class FinancialAutomationRecordUpdateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Optional[str] = Field(None, pattern=_choices_pattern(FINANCIAL_AUTOMATION_STATUS_VALUES))
    entry_direction: Optional[str] = Field(None, pattern=_choices_pattern(FINANCIAL_AUTOMATION_ENTRY_DIRECTION_VALUES))
    settlement_state: Optional[str] = Field(None, pattern=_choices_pattern(FINANCIAL_AUTOMATION_SETTLEMENT_STATE_VALUES))
    description: Optional[str] = Field(None, max_length=255)
    counterparty_id: Optional[int] = None
    bank_account_id: Optional[int] = None
    chart_account_id: Optional[int] = None
    cost_center_id: Optional[int] = None
    domain_type: Optional[str] = Field(None, pattern=_choices_pattern(FINANCIAL_AUTOMATION_DOMAIN_TYPE_VALUES))
    domain_source_id: Optional[int] = None
    document_group_key: Optional[str] = Field(None, max_length=255)
    document_type: Optional[str] = Field(None, pattern=_choices_pattern(FINANCIAL_AUTOMATION_DOCUMENT_TYPE_VALUES))
    document_key: Optional[str] = Field(None, max_length=64)
    external_document_number: Optional[str] = Field(None, max_length=120)
    issuer_name: Optional[str] = Field(None, max_length=255)
    issuer_document: Optional[str] = Field(None, max_length=32)
    recipient_name: Optional[str] = Field(None, max_length=255)
    recipient_document: Optional[str] = Field(None, max_length=32)
    issue_date: Optional[date] = None
    amount: Optional[Decimal] = Field(None, ge=0)
    competence_date: Optional[date] = None
    due_date: Optional[date] = None
    confidence_score: Optional[Decimal] = Field(None, ge=0, le=1)
    validation_notes: Optional[str] = None
    extracted_fields_json: Optional[Dict[str, Any]] = None
    review_flags_json: Optional[List[str]] = None
    normalized_payload_json: Optional[Dict[str, Any]] = None
    metadata_json: Optional[Dict[str, Any]] = None

    @field_validator(
        "description",
        "validation_notes",
        "document_group_key",
        "document_type",
        "document_key",
        "external_document_number",
        "issuer_name",
        "issuer_document",
        "recipient_name",
        "recipient_document",
        mode="before",
    )
    @classmethod
    def normalize_text_fields(cls, value):
        return _normalize_text(value)


class FinancialAutomationBulkStatusInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_id: int
    record_ids: List[int] = Field(..., min_length=1)
    status: str = Field(..., pattern=_choices_pattern(FINANCIAL_AUTOMATION_STATUS_VALUES))
    validation_notes: Optional[str] = None

    @field_validator("validation_notes", mode="before")
    @classmethod
    def normalize_notes(cls, value):
        return _normalize_text(value)


class FinancialAutomationGenerateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_id: int
    record_ids: Optional[List[int]] = None
    only_status: str = Field("validated", pattern=_choices_pattern(FINANCIAL_AUTOMATION_STATUS_VALUES))
    generated_by_user_id: Optional[int] = None

    @model_validator(mode="after")
    def validate_selection(self):
        if self.record_ids is not None and len(self.record_ids) == 0:
            raise ValueError("record_ids não pode ser uma lista vazia.")
        return self


class FinancialAutomationHistoryCreateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_id: int
    record_id: int
    action_type: str = Field(..., min_length=3, max_length=50)
    performed_by_user_id: Optional[int] = None
    payload_before_json: Dict[str, Any] = Field(default_factory=dict)
    payload_after_json: Dict[str, Any] = Field(default_factory=dict)
    metadata_json: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("action_type", mode="before")
    @classmethod
    def normalize_action_type(cls, value):
        return _normalize_text(value)
