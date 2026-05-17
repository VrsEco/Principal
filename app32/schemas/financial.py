from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional

from marshmallow import fields
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from models import FinancialEntry, FinancialEntryAllocation, FinancialSettlement
from models.financial import (
    ALLOCATION_TYPE_VALUES,
    AUTOMATION_TRIGGER_STATUS_VALUES,
    BORDERO_SETTLEMENT_STATUS_VALUES,
    BORDERO_STATUS_VALUES,
    BORDERO_TYPE_VALUES,
    DOMAIN_ENABLEMENT_TYPE_VALUES,
    ENTRY_ORIGIN_VALUES,
    ENTRY_STATUS_VALUES,
    ENTRY_TYPE_VALUES,
    INGESTION_COMPLETION_STATUS_VALUES,
    INGESTION_CONFIDENCE_LEVEL_VALUES,
    INGESTION_REVIEW_STATUS_VALUES,
    INGESTION_SOURCE_VALUES,
    IMPORT_BATCH_STATUS_VALUES,
    IMPORT_ROW_STATUS_VALUES,
    IMPORT_SOURCE_VALUES,
    CLASSIFICATION_OPERATOR_VALUES,
    DOMAIN_SOURCE_KIND_VALUES,
    MOVEMENT_NATURE_VALUES,
    RECONCILIATION_STATUS_VALUES,
    REVIEW_STATUS_VALUES,
    SCHEDULE_FREQUENCY_VALUES,
    SCHEDULE_STATUS_VALUES,
    SETTLEMENT_COMPONENT_TYPE_VALUES,
    SETTLEMENT_STATUS_VALUES,
    SETTLEMENT_TYPE_VALUES,
)
from schemas import ma


def _choices_pattern(values: tuple[str, ...]) -> str:
    return "^(" + "|".join(values) + ")$"


def _digits_only(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    return digits or None


def _normalize_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


class FinancialEntryAllocationSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = FinancialEntryAllocation
        load_instance = True
        include_fk = True

    percentage = fields.Float(allow_none=True)
    allocated_amount = fields.Float(allow_none=True)
    created_at = fields.String(dump_only=True)
    updated_at = fields.String(dump_only=True)


class FinancialSettlementSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = FinancialSettlement
        load_instance = True
        include_fk = True

    principal_amount = fields.Float()
    interest_amount = fields.Float()
    penalty_amount = fields.Float()
    discount_amount = fields.Float()
    fee_amount = fields.Float()
    other_adjustments_amount = fields.Float()
    gross_amount = fields.Float()
    net_amount = fields.Float()
    created_at = fields.String(dump_only=True)
    updated_at = fields.String(dump_only=True)


class FinancialEntrySchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = FinancialEntry
        load_instance = True
        include_fk = True

    original_amount = fields.Float()
    created_at = fields.String(dump_only=True)
    updated_at = fields.String(dump_only=True)
    allocations = fields.Nested(FinancialEntryAllocationSchema, many=True, dump_only=True)
    settlements = fields.Nested(FinancialSettlementSchema, many=True, dump_only=True)


financial_entry_schema = FinancialEntrySchema()
financial_entries_schema = FinancialEntrySchema(many=True)
financial_entry_allocation_schema = FinancialEntryAllocationSchema()
financial_entry_allocations_schema = FinancialEntryAllocationSchema(many=True)
financial_settlement_schema = FinancialSettlementSchema()
financial_settlements_schema = FinancialSettlementSchema(many=True)


class FinancialImportBatchInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_id: int
    batch_code: str = Field(..., min_length=3, max_length=50)
    source_type: str = Field(..., pattern=_choices_pattern(IMPORT_SOURCE_VALUES))
    file_name: Optional[str] = Field(None, max_length=255)
    file_hash: Optional[str] = Field(None, max_length=64)
    uploaded_by_user_id: Optional[int] = None
    uploaded_by_employee_id: Optional[int] = None
    created_by_agent: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = None
    metadata_json: Dict[str, Any] = Field(default_factory=dict)


class FinancialImportRowInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_id: int
    row_number: int = Field(..., ge=1)
    processing_status: str = Field("staged", pattern=_choices_pattern(IMPORT_ROW_STATUS_VALUES))
    document_number: Optional[str] = Field(None, max_length=80)
    description: Optional[str] = Field(None, max_length=255)
    occurred_on: Optional[date] = None
    due_date: Optional[date] = None
    amount: Optional[Decimal] = None
    movement_nature: Optional[str] = Field(None, pattern=_choices_pattern(MOVEMENT_NATURE_VALUES))
    bank_reference: Optional[str] = Field(None, max_length=120)
    counterparty_name: Optional[str] = Field(None, max_length=255)
    raw_payload: Dict[str, Any] = Field(default_factory=dict)
    normalized_payload: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None


class FinancialIngestionRecordInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_id: int
    origin_type: str = Field(..., pattern=_choices_pattern(INGESTION_SOURCE_VALUES))
    origin_reference: Optional[str] = Field(None, max_length=120)
    external_system: Optional[str] = Field(None, max_length=80)
    source_file_name: Optional[str] = Field(None, max_length=255)
    source_mime_type: Optional[str] = Field(None, max_length=120)
    source_channel: Optional[str] = Field(None, max_length=50)
    import_batch_id: Optional[int] = None
    related_schedule_id: Optional[int] = None
    related_entry_id: Optional[int] = None
    completion_status: str = Field("received", pattern=_choices_pattern(INGESTION_COMPLETION_STATUS_VALUES))
    review_status: str = Field("pending_review", pattern=_choices_pattern(INGESTION_REVIEW_STATUS_VALUES))
    confidence_score: Optional[Decimal] = Field(None, ge=0, le=1)
    confidence_level: Optional[str] = Field(None, pattern=_choices_pattern(INGESTION_CONFIDENCE_LEVEL_VALUES))
    raw_payload_json: Dict[str, Any] = Field(default_factory=dict)
    normalized_payload_json: Dict[str, Any] = Field(default_factory=dict)
    extracted_text: Optional[str] = None
    llm_response_json: Dict[str, Any] = Field(default_factory=dict)
    review_notes: Optional[str] = None
    created_by_user_id: Optional[int] = None
    reviewed_by_user_id: Optional[int] = None
    metadata_json: Dict[str, Any] = Field(default_factory=dict)

    @field_validator(
        "origin_reference",
        "external_system",
        "source_file_name",
        "source_mime_type",
        "source_channel",
        "review_notes",
        mode="before",
    )
    @classmethod
    def normalize_text_fields(cls, value):
        return _normalize_text(value)


class FinancialIngestionRecordUpdateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    origin_reference: Optional[str] = Field(None, max_length=120)
    external_system: Optional[str] = Field(None, max_length=80)
    source_file_name: Optional[str] = Field(None, max_length=255)
    source_mime_type: Optional[str] = Field(None, max_length=120)
    source_channel: Optional[str] = Field(None, max_length=50)
    import_batch_id: Optional[int] = None
    related_schedule_id: Optional[int] = None
    related_entry_id: Optional[int] = None
    completion_status: Optional[str] = Field(None, pattern=_choices_pattern(INGESTION_COMPLETION_STATUS_VALUES))
    review_status: Optional[str] = Field(None, pattern=_choices_pattern(INGESTION_REVIEW_STATUS_VALUES))
    confidence_score: Optional[Decimal] = Field(None, ge=0, le=1)
    confidence_level: Optional[str] = Field(None, pattern=_choices_pattern(INGESTION_CONFIDENCE_LEVEL_VALUES))
    raw_payload_json: Optional[Dict[str, Any]] = None
    normalized_payload_json: Optional[Dict[str, Any]] = None
    extracted_text: Optional[str] = None
    llm_response_json: Optional[Dict[str, Any]] = None
    review_notes: Optional[str] = None
    reviewed_by_user_id: Optional[int] = None
    metadata_json: Optional[Dict[str, Any]] = None

    @field_validator(
        "origin_reference",
        "external_system",
        "source_file_name",
        "source_mime_type",
        "source_channel",
        "review_notes",
        mode="before",
    )
    @classmethod
    def normalize_text_fields(cls, value):
        return _normalize_text(value)


class FinancialBankAccountInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_id: int
    code: Optional[str] = Field(None, max_length=30)
    name: str = Field(..., min_length=2, max_length=120)
    bank_code: Optional[str] = Field(None, max_length=20)
    bank_name: Optional[str] = Field(None, max_length=120)
    branch_number: Optional[str] = Field(None, max_length=20)
    account_number: Optional[str] = Field(None, max_length=30)
    account_digit: Optional[str] = Field(None, max_length=10)
    holder_name: Optional[str] = Field(None, max_length=255)
    holder_document: Optional[str] = Field(None, max_length=50)
    pix_key: Optional[str] = Field(None, max_length=120)
    currency_code: str = Field("BRL", min_length=3, max_length=3)
    overdraft_limit: Optional[Decimal] = Field(None, ge=0)
    is_active: bool = True
    metadata_json: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("code", mode="before")
    @classmethod
    def normalize_code(cls, value):
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @field_validator("holder_document", mode="before")
    @classmethod
    def normalize_holder_document(cls, value):
        return _digits_only(value)

    @field_validator("currency_code", mode="before")
    @classmethod
    def normalize_currency_code(cls, value):
        if value is None or value == "":
            return "BRL"
        normalized = str(value).strip().upper()
        aliases = {
            "R$": "BRL",
            "REAL": "BRL",
            "REAIS": "BRL",
        }
        return aliases.get(normalized, normalized)


class FinancialBankAccountUpdateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: Optional[str] = Field(None, min_length=1, max_length=30)
    name: Optional[str] = Field(None, min_length=2, max_length=120)
    bank_code: Optional[str] = Field(None, max_length=20)
    bank_name: Optional[str] = Field(None, max_length=120)
    branch_number: Optional[str] = Field(None, max_length=20)
    account_number: Optional[str] = Field(None, max_length=30)
    account_digit: Optional[str] = Field(None, max_length=10)
    holder_name: Optional[str] = Field(None, max_length=255)
    holder_document: Optional[str] = Field(None, max_length=50)
    pix_key: Optional[str] = Field(None, max_length=120)
    currency_code: Optional[str] = Field(None, min_length=3, max_length=3)
    overdraft_limit: Optional[Decimal] = Field(None, ge=0)
    is_active: Optional[bool] = None
    metadata_json: Optional[Dict[str, Any]] = None

    @field_validator("code", mode="before")
    @classmethod
    def normalize_code(cls, value):
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @field_validator("holder_document", mode="before")
    @classmethod
    def normalize_holder_document(cls, value):
        return _digits_only(value)

    @field_validator("currency_code", mode="before")
    @classmethod
    def normalize_currency_code(cls, value):
        if value is None or value == "":
            return None
        normalized = str(value).strip().upper()
        aliases = {
            "R$": "BRL",
            "REAL": "BRL",
            "REAIS": "BRL",
        }
        return aliases.get(normalized, normalized)


class FinancialChartAccountInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_id: int
    parent_id: Optional[int] = None
    code: Optional[str] = Field(None, max_length=30)
    code_suffix: Optional[str] = Field(None, max_length=10)
    reduced_code: Optional[str] = Field(None, max_length=3)
    external_code: Optional[str] = Field(None, max_length=120)
    name: str = Field(..., min_length=2, max_length=120)
    movement_nature: Optional[str] = Field(None, pattern=_choices_pattern(MOVEMENT_NATURE_VALUES))
    accepts_posting: bool = True
    account_level_type: Optional[str] = Field(None, pattern="^(analytic|synthetic)$")
    is_active: bool = True
    metadata_json: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("code", mode="before")
    @classmethod
    def normalize_code(cls, value):
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @field_validator("code_suffix", mode="before")
    @classmethod
    def normalize_code_suffix(cls, value):
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        if not text.isdigit():
            raise ValueError("code_suffix deve conter apenas números.")
        return text

    @field_validator("reduced_code", mode="before")
    @classmethod
    def normalize_reduced_code(cls, value):
        if value is None:
            return None
        text = str(value).strip()
        return text.lower() or None


class FinancialChartAccountUpdateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    parent_id: Optional[int] = None
    code: Optional[str] = Field(None, max_length=30)
    code_suffix: Optional[str] = Field(None, max_length=10)
    reduced_code: Optional[str] = Field(None, max_length=3)
    external_code: Optional[str] = Field(None, max_length=120)
    name: Optional[str] = Field(None, min_length=2, max_length=120)
    movement_nature: Optional[str] = Field(None, pattern=_choices_pattern(MOVEMENT_NATURE_VALUES))
    accepts_posting: Optional[bool] = None
    account_level_type: Optional[str] = Field(None, pattern="^(analytic|synthetic)$")
    is_active: Optional[bool] = None
    metadata_json: Optional[Dict[str, Any]] = None

    @field_validator("code", mode="before")
    @classmethod
    def normalize_code(cls, value):
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @field_validator("code_suffix", mode="before")
    @classmethod
    def normalize_code_suffix(cls, value):
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        if not text.isdigit():
            raise ValueError("code_suffix deve conter apenas números.")
        return text

    @field_validator("reduced_code", mode="before")
    @classmethod
    def normalize_reduced_code(cls, value):
        if value is None:
            return None
        text = str(value).strip()
        return text.lower() or None


class FinancialCostCenterInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_id: int
    parent_id: Optional[int] = None
    manager_employee_id: Optional[int] = None
    code: Optional[str] = Field(None, max_length=30)
    code_suffix: Optional[str] = Field(None, max_length=10)
    reduced_code: Optional[str] = Field(None, max_length=3)
    external_code: Optional[str] = Field(None, max_length=120)
    name: str = Field(..., min_length=2, max_length=120)
    description: Optional[str] = None
    accepts_posting: bool = True
    account_level_type: Optional[str] = Field(None, pattern="^(analytic|synthetic)$")
    is_active: bool = True
    is_default_suggestion: bool = False
    metadata_json: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("code", mode="before")
    @classmethod
    def normalize_code(cls, value):
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @field_validator("code_suffix", mode="before")
    @classmethod
    def normalize_code_suffix(cls, value):
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        if not text.isdigit():
            raise ValueError("code_suffix deve conter apenas números.")
        return text

    @field_validator("reduced_code", mode="before")
    @classmethod
    def normalize_reduced_code(cls, value):
        if value is None:
            return None
        text = str(value).strip()
        return text.lower() or None


class FinancialCostCenterUpdateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    parent_id: Optional[int] = None
    manager_employee_id: Optional[int] = None
    code: Optional[str] = Field(None, max_length=30)
    code_suffix: Optional[str] = Field(None, max_length=10)
    reduced_code: Optional[str] = Field(None, max_length=3)
    external_code: Optional[str] = Field(None, max_length=120)
    name: Optional[str] = Field(None, min_length=2, max_length=120)
    description: Optional[str] = None
    accepts_posting: Optional[bool] = None
    account_level_type: Optional[str] = Field(None, pattern="^(analytic|synthetic)$")
    is_active: Optional[bool] = None
    is_default_suggestion: Optional[bool] = None
    metadata_json: Optional[Dict[str, Any]] = None

    @field_validator("code", mode="before")
    @classmethod
    def normalize_code(cls, value):
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @field_validator("code_suffix", mode="before")
    @classmethod
    def normalize_code_suffix(cls, value):
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        if not text.isdigit():
            raise ValueError("code_suffix deve conter apenas números.")
        return text

    @field_validator("reduced_code", mode="before")
    @classmethod
    def normalize_reduced_code(cls, value):
        if value is None:
            return None
        text = str(value).strip()
        return text.lower() or None


class _SimpleFinancialCatalogBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @field_validator("code", "name", "external_code", mode="before", check_fields=False)
    @classmethod
    def normalize_common_text(cls, value):
        return _normalize_text(value)


class FinancialAccountCategoryInput(_SimpleFinancialCatalogBase):
    company_id: int
    code: Optional[str] = Field(None, max_length=30)
    name: str = Field(..., min_length=2, max_length=120)
    external_code: Optional[str] = Field(None, max_length=120)
    description: Optional[str] = None
    is_active: bool = True
    metadata_json: Dict[str, Any] = Field(default_factory=dict)


class FinancialAccountCategoryUpdateInput(_SimpleFinancialCatalogBase):
    code: Optional[str] = Field(None, min_length=1, max_length=30)
    name: Optional[str] = Field(None, min_length=2, max_length=120)
    external_code: Optional[str] = Field(None, max_length=120)
    description: Optional[str] = None
    is_active: Optional[bool] = None
    metadata_json: Optional[Dict[str, Any]] = None



class FinancialAssetAccountInput(_SimpleFinancialCatalogBase):
    company_id: int
    code: Optional[str] = Field(None, max_length=30)
    name: str = Field(..., min_length=2, max_length=120)
    patrimonial_type: Optional[str] = Field("asset", pattern="^(asset|liability|equity)$")
    account_class: Optional[str] = Field("current", pattern="^(current|non_current)$")
    category_id: Optional[int] = None
    chart_account_ids: List[int] = Field(default_factory=list)
    config_mode: Optional[str] = Field("due_dates", pattern="^(due_dates|bank_balances|manual_value)$")
    due_scope: Optional[str] = Field("overdue", pattern="^(overdue|all_future|due_in_days)$")
    due_in_days: Optional[int] = Field(None, ge=0, le=3650)
    bank_account_ids: List[int] = Field(default_factory=list)
    manual_value: Optional[Decimal] = Field(None, ge=0)
    description: Optional[str] = None
    is_active: bool = True
    metadata_json: Dict[str, Any] = Field(default_factory=dict)


class FinancialAssetAccountUpdateInput(_SimpleFinancialCatalogBase):
    code: Optional[str] = Field(None, min_length=1, max_length=30)
    name: Optional[str] = Field(None, min_length=2, max_length=120)
    patrimonial_type: Optional[str] = Field(None, pattern="^(asset|liability|equity)$")
    account_class: Optional[str] = Field(None, pattern="^(current|non_current)$")
    category_id: Optional[int] = None
    chart_account_ids: Optional[List[int]] = None
    config_mode: Optional[str] = Field(None, pattern="^(due_dates|bank_balances|manual_value)$")
    due_scope: Optional[str] = Field(None, pattern="^(overdue|all_future|due_in_days)$")
    due_in_days: Optional[int] = Field(None, ge=0, le=3650)
    bank_account_ids: Optional[List[int]] = None
    manual_value: Optional[Decimal] = Field(None, ge=0)
    description: Optional[str] = None
    is_active: Optional[bool] = None
    metadata_json: Optional[Dict[str, Any]] = None


class FinancialCorrectionIndexInput(_SimpleFinancialCatalogBase):
    company_id: int
    code: Optional[str] = Field(None, max_length=30)
    name: str = Field(..., min_length=2, max_length=120)
    chart_account_id: Optional[int] = None
    is_default_receivable: bool = False
    is_default_payable: bool = False
    interest_rate: Optional[Decimal] = Field(None, ge=0, le=100)
    interest_period: Optional[str] = Field("daily", pattern="^(daily|monthly)$")
    penalty_rate: Optional[Decimal] = Field(None, ge=0, le=100)
    penalty_period: Optional[str] = Field("daily", pattern="^(daily|monthly)$")
    penalty_limit_rate: Optional[Decimal] = Field(None, ge=0, le=100)
    description: Optional[str] = None
    is_active: bool = True
    metadata_json: Dict[str, Any] = Field(default_factory=dict)


class FinancialCorrectionIndexUpdateInput(_SimpleFinancialCatalogBase):
    code: Optional[str] = Field(None, min_length=1, max_length=30)
    name: Optional[str] = Field(None, min_length=2, max_length=120)
    chart_account_id: Optional[int] = None
    is_default_receivable: Optional[bool] = None
    is_default_payable: Optional[bool] = None
    interest_rate: Optional[Decimal] = Field(None, ge=0, le=100)
    interest_period: Optional[str] = Field(None, pattern="^(daily|monthly)$")
    penalty_rate: Optional[Decimal] = Field(None, ge=0, le=100)
    penalty_period: Optional[str] = Field(None, pattern="^(daily|monthly)$")
    penalty_limit_rate: Optional[Decimal] = Field(None, ge=0, le=100)
    description: Optional[str] = None
    is_active: Optional[bool] = None
    metadata_json: Optional[Dict[str, Any]] = None


class FinancialDiscountRuleInput(_SimpleFinancialCatalogBase):
    company_id: int
    code: Optional[str] = Field(None, max_length=30)
    name: str = Field(..., min_length=2, max_length=120)
    external_code: Optional[str] = Field(None, max_length=120)
    chart_account_id: Optional[int] = None
    is_default_receivable: bool = False
    is_default_payable: bool = False
    discount_type: Optional[str] = Field(None, pattern="^(percentage|fixed)$")
    value: Optional[Decimal] = Field(None, ge=0)
    description: Optional[str] = None
    is_active: bool = True
    metadata_json: Dict[str, Any] = Field(default_factory=dict)


class FinancialDiscountRuleUpdateInput(_SimpleFinancialCatalogBase):
    code: Optional[str] = Field(None, min_length=1, max_length=30)
    name: Optional[str] = Field(None, min_length=2, max_length=120)
    external_code: Optional[str] = Field(None, max_length=120)
    chart_account_id: Optional[int] = None
    is_default_receivable: Optional[bool] = None
    is_default_payable: Optional[bool] = None
    discount_type: Optional[str] = Field(None, pattern="^(percentage|fixed)$")
    value: Optional[Decimal] = Field(None, ge=0)
    description: Optional[str] = None
    is_active: Optional[bool] = None
    metadata_json: Optional[Dict[str, Any]] = None


class FinancialPaymentMethodInput(_SimpleFinancialCatalogBase):
    company_id: int
    code: Optional[str] = Field(None, max_length=30)
    name: str = Field(..., min_length=2, max_length=120)
    external_code: Optional[str] = Field(None, max_length=120)
    operation_type: Optional[str] = Field("both", pattern="^(payable|receivable|both)$")
    settlement_days: Optional[int] = Field(0, ge=0, le=3650)
    description: Optional[str] = None
    is_active: bool = True
    is_default_suggestion: bool = False
    metadata_json: Dict[str, Any] = Field(default_factory=dict)


class FinancialPaymentMethodUpdateInput(_SimpleFinancialCatalogBase):
    code: Optional[str] = Field(None, min_length=1, max_length=30)
    name: Optional[str] = Field(None, min_length=2, max_length=120)
    external_code: Optional[str] = Field(None, max_length=120)
    operation_type: Optional[str] = Field(None, pattern="^(payable|receivable|both)$")
    settlement_days: Optional[int] = Field(None, ge=0, le=3650)
    description: Optional[str] = None
    is_active: Optional[bool] = None
    is_default_suggestion: Optional[bool] = None
    metadata_json: Optional[Dict[str, Any]] = None


class FinancialDomainEnablementInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_id: int
    domain_type: str = Field(..., pattern=_choices_pattern(DOMAIN_ENABLEMENT_TYPE_VALUES))
    source_id: int = Field(..., ge=1)
    is_enabled: bool = True
    is_default_suggestion: bool = False
    notes: Optional[str] = None
    metadata_json: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("notes", mode="before")
    @classmethod
    def normalize_notes(cls, value):
        return _normalize_text(value)


class FinancialDomainEnablementUpdateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_enabled: Optional[bool] = None
    is_default_suggestion: Optional[bool] = None
    notes: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None

    @field_validator("notes", mode="before")
    @classmethod
    def normalize_notes(cls, value):
        return _normalize_text(value)


class FinancialManualDomainInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_id: int
    domain_type: str = Field(..., pattern=_choices_pattern(DOMAIN_ENABLEMENT_TYPE_VALUES))
    code: Optional[str] = Field(None, max_length=40)
    name: str = Field(..., min_length=2, max_length=160)
    is_active: bool = True
    is_enabled: bool = True
    is_default_suggestion: bool = False
    notes: Optional[str] = None
    metadata_json: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("code", "name", "notes", mode="before")
    @classmethod
    def normalize_text_fields(cls, value):
        return _normalize_text(value)


class FinancialManualDomainUpdateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    domain_type: Optional[str] = Field(None, pattern=_choices_pattern(DOMAIN_ENABLEMENT_TYPE_VALUES))
    code: Optional[str] = Field(None, max_length=40)
    name: Optional[str] = Field(None, min_length=2, max_length=160)
    is_active: Optional[bool] = None
    is_enabled: Optional[bool] = None
    is_default_suggestion: Optional[bool] = None
    notes: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None

    @field_validator("code", "name", "notes", mode="before")
    @classmethod
    def normalize_text_fields(cls, value):
        return _normalize_text(value)


class FinancialCounterpartyInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_id: int
    default_chart_account_id: Optional[int] = None
    default_cost_center_id: Optional[int] = None
    code: Optional[str] = Field(None, max_length=30)
    name: str = Field(..., min_length=2, max_length=120)
    legal_name: Optional[str] = Field(None, max_length=255)
    document_number: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    pix_key: Optional[str] = Field(None, max_length=120)
    notes: Optional[str] = None
    is_active: bool = True
    is_customer: bool = False
    is_supplier: bool = True
    metadata_json: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("code", mode="before")
    @classmethod
    def normalize_code(cls, value):
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @field_validator("document_number", mode="before")
    @classmethod
    def normalize_document_number(cls, value):
        return _digits_only(value)


class FinancialCounterpartyUpdateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    default_chart_account_id: Optional[int] = None
    default_cost_center_id: Optional[int] = None
    code: Optional[str] = Field(None, min_length=1, max_length=30)
    name: Optional[str] = Field(None, min_length=2, max_length=120)
    legal_name: Optional[str] = Field(None, max_length=255)
    document_number: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    pix_key: Optional[str] = Field(None, max_length=120)
    notes: Optional[str] = None
    is_active: Optional[bool] = None
    is_customer: Optional[bool] = None
    is_supplier: Optional[bool] = None
    metadata_json: Optional[Dict[str, Any]] = None

    @field_validator("code", mode="before")
    @classmethod
    def normalize_code(cls, value):
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @field_validator("document_number", mode="before")
    @classmethod
    def normalize_document_number(cls, value):
        return _digits_only(value)


class FinancialScheduleAllocationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chart_account_id: Optional[int] = None
    cost_center_id: Optional[int] = None
    budget_version_id: Optional[int] = None
    budget_line_id: Optional[int] = None
    budget_contract_id: Optional[int] = None
    budget_document_id: Optional[int] = None
    domain_type: Optional[str] = Field(None, pattern=_choices_pattern(DOMAIN_ENABLEMENT_TYPE_VALUES))
    domain_source_kind: Optional[str] = Field("routine", pattern=_choices_pattern(DOMAIN_SOURCE_KIND_VALUES))
    domain_source_id: Optional[int] = None
    domain_label: Optional[str] = Field(None, max_length=255)
    allocation_type: str = Field(..., pattern=_choices_pattern(ALLOCATION_TYPE_VALUES))
    percentage: Optional[Decimal] = Field(None, ge=0)
    allocated_amount: Optional[Decimal] = None
    notes: Optional[str] = None
    metadata_json: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_allocation(self):
        if self.allocation_type == "percentage" and self.percentage is None:
            raise ValueError("Rateio percentual exige campo percentage.")
        if self.allocation_type == "amount" and self.allocated_amount is None:
            raise ValueError("Rateio por valor exige campo allocated_amount.")
        return self


class FinancialScheduleCreateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_id: int
    schedule_code: str = Field(..., min_length=3, max_length=50)
    name: str = Field(..., min_length=3, max_length=120)
    entry_type: str = Field(..., pattern=_choices_pattern(ENTRY_TYPE_VALUES))
    movement_nature: str = Field(..., pattern=_choices_pattern(MOVEMENT_NATURE_VALUES))
    origin_type: str = Field("manual", pattern=_choices_pattern(ENTRY_ORIGIN_VALUES))
    status: str = Field("draft", pattern=_choices_pattern(SCHEDULE_STATUS_VALUES))
    frequency: str = Field("monthly", pattern=_choices_pattern(SCHEDULE_FREQUENCY_VALUES))
    interval_value: int = Field(default=1, ge=1)
    start_date: date
    competence_date: Optional[date] = None
    end_date: Optional[date] = None
    first_due_date: date
    next_due_date: Optional[date] = None
    day_of_month: Optional[int] = Field(None, ge=1, le=31)
    weekday: Optional[int] = Field(None, ge=0, le=6)
    description: str = Field(..., min_length=3, max_length=255)
    memo: Optional[str] = None
    document_number_prefix: Optional[str] = Field(None, max_length=40)
    template_amount: Decimal = Field(..., ge=0)
    currency_code: str = Field("BRL", min_length=3, max_length=3)
    auto_post: bool = False
    generate_advance_days: int = Field(default=0, ge=0, le=365)
    bank_account_id: Optional[int] = None
    counterparty_id: Optional[int] = None
    chart_account_id: Optional[int] = None
    cost_center_id: Optional[int] = None
    budget_line_id: Optional[int] = None
    budget_contract_id: Optional[int] = None
    budget_document_id: Optional[int] = None
    activity_id: Optional[int] = None
    process_instance_id: Optional[int] = None
    routine_id: Optional[int] = None
    created_by_user_id: Optional[int] = None
    created_by_employee_id: Optional[int] = None
    created_by_agent: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = None
    metadata_json: Dict[str, Any] = Field(default_factory=dict)
    allocations: List[FinancialScheduleAllocationInput] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_dates(self):
        effective_competence_date = self.competence_date or self.start_date
        if self.competence_date is None:
            self.competence_date = effective_competence_date
        if self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date não pode ser menor que start_date.")
        if self.first_due_date < effective_competence_date:
            raise ValueError("first_due_date não pode ser menor que competence_date.")
        if self.next_due_date and self.next_due_date < self.first_due_date:
            raise ValueError("next_due_date não pode ser menor que first_due_date.")
        if self.frequency == "monthly" and self.day_of_month is None:
            self.day_of_month = min(self.first_due_date.day, 28)
        if self.frequency == "weekly" and self.weekday is None:
            self.weekday = self.first_due_date.weekday()
        return self


class FinancialScheduleUpdateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schedule_code: Optional[str] = Field(None, min_length=3, max_length=50)
    name: Optional[str] = Field(None, min_length=3, max_length=120)
    entry_type: Optional[str] = Field(None, pattern=_choices_pattern(ENTRY_TYPE_VALUES))
    movement_nature: Optional[str] = Field(None, pattern=_choices_pattern(MOVEMENT_NATURE_VALUES))
    origin_type: Optional[str] = Field(None, pattern=_choices_pattern(ENTRY_ORIGIN_VALUES))
    status: Optional[str] = Field(None, pattern=_choices_pattern(SCHEDULE_STATUS_VALUES))
    frequency: Optional[str] = Field(None, pattern=_choices_pattern(SCHEDULE_FREQUENCY_VALUES))
    interval_value: Optional[int] = Field(None, ge=1)
    start_date: Optional[date] = None
    competence_date: Optional[date] = None
    end_date: Optional[date] = None
    first_due_date: Optional[date] = None
    next_due_date: Optional[date] = None
    day_of_month: Optional[int] = Field(None, ge=1, le=31)
    weekday: Optional[int] = Field(None, ge=0, le=6)
    description: Optional[str] = Field(None, min_length=3, max_length=255)
    memo: Optional[str] = None
    document_number_prefix: Optional[str] = Field(None, max_length=40)
    template_amount: Optional[Decimal] = Field(None, ge=0)
    currency_code: Optional[str] = Field(None, min_length=3, max_length=3)
    auto_post: Optional[bool] = None
    generate_advance_days: Optional[int] = Field(None, ge=0, le=365)
    bank_account_id: Optional[int] = None
    counterparty_id: Optional[int] = None
    chart_account_id: Optional[int] = None
    cost_center_id: Optional[int] = None
    budget_line_id: Optional[int] = None
    budget_contract_id: Optional[int] = None
    budget_document_id: Optional[int] = None
    activity_id: Optional[int] = None
    process_instance_id: Optional[int] = None
    routine_id: Optional[int] = None
    notes: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None
    allocations: List[FinancialScheduleAllocationInput] = Field(default_factory=list)


class FinancialAutomationRuleCreateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_id: int
    rule_code: str = Field(..., min_length=3, max_length=50)
    name: str = Field(..., min_length=3, max_length=120)
    process_id: Optional[int] = None
    activity_id: Optional[int] = None
    trigger_status: str = Field("any", pattern=_choices_pattern(AUTOMATION_TRIGGER_STATUS_VALUES))
    trigger_on_create: bool = True
    is_active: bool = True
    auto_activate_schedule: bool = True
    schedule_name_template: str = Field(..., min_length=3, max_length=160)
    description_template: str = Field(..., min_length=3, max_length=255)
    entry_type: str = Field("forecast", pattern=_choices_pattern(ENTRY_TYPE_VALUES))
    movement_nature: str = Field(..., pattern=_choices_pattern(MOVEMENT_NATURE_VALUES))
    origin_type: str = Field("process", pattern=_choices_pattern(ENTRY_ORIGIN_VALUES))
    frequency: str = Field("one_time", pattern=_choices_pattern(SCHEDULE_FREQUENCY_VALUES))
    interval_value: int = Field(default=1, ge=1)
    start_offset_days: int = Field(default=0, ge=0, le=3650)
    due_offset_days: int = Field(default=0, ge=0, le=3650)
    template_amount: Decimal = Field(default=Decimal("0"), ge=0)
    currency_code: str = Field("BRL", min_length=3, max_length=3)
    auto_post: bool = False
    generate_advance_days: int = Field(default=0, ge=0, le=365)
    bank_account_id: Optional[int] = None
    counterparty_id: Optional[int] = None
    chart_account_id: Optional[int] = None
    cost_center_id: Optional[int] = None
    routine_id: Optional[int] = None
    notes: Optional[str] = None
    metadata_json: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_scope(self):
        if not self.process_id and not self.activity_id:
            raise ValueError("A regra de automação precisa de process_id ou activity_id.")
        return self


class FinancialAutomationRuleUpdateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rule_code: Optional[str] = Field(None, min_length=3, max_length=50)
    name: Optional[str] = Field(None, min_length=3, max_length=120)
    process_id: Optional[int] = None
    activity_id: Optional[int] = None
    trigger_status: Optional[str] = Field(None, pattern=_choices_pattern(AUTOMATION_TRIGGER_STATUS_VALUES))
    trigger_on_create: Optional[bool] = None
    is_active: Optional[bool] = None
    auto_activate_schedule: Optional[bool] = None
    schedule_name_template: Optional[str] = Field(None, min_length=3, max_length=160)
    description_template: Optional[str] = Field(None, min_length=3, max_length=255)
    entry_type: Optional[str] = Field(None, pattern=_choices_pattern(ENTRY_TYPE_VALUES))
    movement_nature: Optional[str] = Field(None, pattern=_choices_pattern(MOVEMENT_NATURE_VALUES))
    origin_type: Optional[str] = Field(None, pattern=_choices_pattern(ENTRY_ORIGIN_VALUES))
    frequency: Optional[str] = Field(None, pattern=_choices_pattern(SCHEDULE_FREQUENCY_VALUES))
    interval_value: Optional[int] = Field(None, ge=1)
    start_offset_days: Optional[int] = Field(None, ge=0, le=3650)
    due_offset_days: Optional[int] = Field(None, ge=0, le=3650)
    template_amount: Optional[Decimal] = Field(None, ge=0)
    currency_code: Optional[str] = Field(None, min_length=3, max_length=3)
    auto_post: Optional[bool] = None
    generate_advance_days: Optional[int] = Field(None, ge=0, le=365)
    bank_account_id: Optional[int] = None
    counterparty_id: Optional[int] = None
    chart_account_id: Optional[int] = None
    cost_center_id: Optional[int] = None
    routine_id: Optional[int] = None
    notes: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None


class FinancialClassificationRuleInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_id: int
    name: str = Field(..., min_length=3, max_length=120)
    priority: int = Field(default=100, ge=0)
    is_active: bool = True
    source_type: Optional[str] = Field(None, pattern=_choices_pattern(IMPORT_SOURCE_VALUES))
    field_name: str = Field(..., min_length=2, max_length=50)
    operator: str = Field(default="contains", pattern=_choices_pattern(CLASSIFICATION_OPERATOR_VALUES))
    match_value: str = Field(..., min_length=1, max_length=255)
    entry_type: Optional[str] = Field(None, pattern=_choices_pattern(ENTRY_TYPE_VALUES))
    movement_nature: Optional[str] = Field(None, pattern=_choices_pattern(MOVEMENT_NATURE_VALUES))
    chart_account_id: Optional[int] = None
    cost_center_id: Optional[int] = None
    activity_id: Optional[int] = None
    process_instance_id: Optional[int] = None
    routine_id: Optional[int] = None
    counterparty_hint: Optional[str] = Field(None, max_length=255)
    notes: Optional[str] = None
    metadata_json: Dict[str, Any] = Field(default_factory=dict)


class FinancialClassificationRuleUpdateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = Field(None, min_length=3, max_length=120)
    priority: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None
    source_type: Optional[str] = Field(None, pattern=_choices_pattern(IMPORT_SOURCE_VALUES))
    field_name: Optional[str] = Field(None, min_length=2, max_length=50)
    operator: Optional[str] = Field(None, pattern=_choices_pattern(CLASSIFICATION_OPERATOR_VALUES))
    match_value: Optional[str] = Field(None, min_length=1, max_length=255)
    entry_type: Optional[str] = Field(None, pattern=_choices_pattern(ENTRY_TYPE_VALUES))
    movement_nature: Optional[str] = Field(None, pattern=_choices_pattern(MOVEMENT_NATURE_VALUES))
    chart_account_id: Optional[int] = None
    cost_center_id: Optional[int] = None
    activity_id: Optional[int] = None
    process_instance_id: Optional[int] = None
    routine_id: Optional[int] = None
    counterparty_hint: Optional[str] = Field(None, max_length=255)
    notes: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None


class FinancialClassificationMemoryUpdateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    supplier_name: Optional[str] = Field(None, max_length=255)
    supplier_document: Optional[str] = Field(None, max_length=50)
    description_pattern: Optional[str] = Field(None, max_length=255)
    product_hint: Optional[str] = Field(None, max_length=255)
    amount_range_min: Optional[Decimal] = None
    amount_range_max: Optional[Decimal] = None
    entry_type: Optional[str] = Field(None, pattern=_choices_pattern(ENTRY_TYPE_VALUES))
    movement_nature: Optional[str] = Field(None, pattern=_choices_pattern(MOVEMENT_NATURE_VALUES))
    chart_account_id: Optional[int] = None
    cost_center_id: Optional[int] = None
    activity_id: Optional[int] = None
    process_instance_id: Optional[int] = None
    routine_id: Optional[int] = None
    counterparty_hint: Optional[str] = Field(None, max_length=255)
    confidence_score: Optional[Decimal] = Field(None, ge=0, le=1)
    source: Optional[str] = None
    is_active: Optional[bool] = None
    metadata_json: Optional[Dict[str, Any]] = None

    @model_validator(mode="after")
    def validate_amount_range(self):
        if (
            self.amount_range_min is not None
            and self.amount_range_max is not None
            and self.amount_range_min > self.amount_range_max
        ):
            raise ValueError("amount_range_min não pode ser maior que amount_range_max.")
        return self


class FinancialEntryCreateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_id: int
    entry_code: str = Field(..., min_length=3, max_length=50)
    entry_type: str = Field(..., pattern=_choices_pattern(ENTRY_TYPE_VALUES))
    movement_nature: str = Field(..., pattern=_choices_pattern(MOVEMENT_NATURE_VALUES))
    origin_type: str = Field("manual", pattern=_choices_pattern(ENTRY_ORIGIN_VALUES))
    status: str = Field("draft", pattern=_choices_pattern(ENTRY_STATUS_VALUES))
    review_status: str = Field("pending_review", pattern=_choices_pattern(REVIEW_STATUS_VALUES))
    description: str = Field(..., min_length=3, max_length=255)
    memo: Optional[str] = None
    document_number: Optional[str] = Field(None, max_length=80)
    external_reference: Optional[str] = Field(None, max_length=120)
    origin_reference: Optional[str] = Field(None, max_length=120)
    financial_schedule_id: Optional[int] = None
    issue_date: Optional[date] = None
    competence_date: date
    due_date: Optional[date] = None
    occurred_on: Optional[date] = None
    original_amount: Decimal = Field(..., ge=0)
    currency_code: str = Field("BRL", min_length=3, max_length=3)
    bank_account_id: Optional[int] = None
    counterparty_id: Optional[int] = None
    chart_account_id: Optional[int] = None
    cost_center_id: Optional[int] = None
    budget_line_id: Optional[int] = None
    budget_contract_id: Optional[int] = None
    budget_document_id: Optional[int] = None
    activity_id: Optional[int] = None
    process_instance_id: Optional[int] = None
    routine_id: Optional[int] = None
    created_by_user_id: Optional[int] = None
    created_by_employee_id: Optional[int] = None
    created_by_agent: Optional[str] = Field(None, max_length=50)
    approved_by_user_id: Optional[int] = None
    notes: Optional[str] = None
    metadata_json: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_operational_link(self):
        if self.origin_type in {"process", "routine", "sapiens"}:
            if not self.activity_id and not self.process_instance_id:
                raise ValueError(
                    "Lançamentos de origem process/routine/sapiens exigem activity_id ou process_instance_id."
                )
        return self


class FinancialEntryUpdateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entry_code: Optional[str] = Field(None, min_length=3, max_length=50)
    entry_type: Optional[str] = Field(None, pattern=_choices_pattern(ENTRY_TYPE_VALUES))
    movement_nature: Optional[str] = Field(None, pattern=_choices_pattern(MOVEMENT_NATURE_VALUES))
    origin_type: Optional[str] = Field(None, pattern=_choices_pattern(ENTRY_ORIGIN_VALUES))
    status: Optional[str] = Field(None, pattern=_choices_pattern(ENTRY_STATUS_VALUES))
    review_status: Optional[str] = Field(None, pattern=_choices_pattern(REVIEW_STATUS_VALUES))
    description: Optional[str] = Field(None, min_length=3, max_length=255)
    memo: Optional[str] = None
    document_number: Optional[str] = Field(None, max_length=80)
    external_reference: Optional[str] = Field(None, max_length=120)
    origin_reference: Optional[str] = Field(None, max_length=120)
    financial_schedule_id: Optional[int] = None
    issue_date: Optional[date] = None
    competence_date: Optional[date] = None
    due_date: Optional[date] = None
    occurred_on: Optional[date] = None
    original_amount: Optional[Decimal] = Field(None, ge=0)
    currency_code: Optional[str] = Field(None, min_length=3, max_length=3)
    bank_account_id: Optional[int] = None
    counterparty_id: Optional[int] = None
    chart_account_id: Optional[int] = None
    cost_center_id: Optional[int] = None
    budget_line_id: Optional[int] = None
    budget_contract_id: Optional[int] = None
    budget_document_id: Optional[int] = None
    activity_id: Optional[int] = None
    process_instance_id: Optional[int] = None
    routine_id: Optional[int] = None
    approved_by_user_id: Optional[int] = None
    notes: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None
    reconciled: Optional[bool] = None
    unlock_reconciliation: Optional[bool] = None
    reconciliation_unlock_reason: Optional[str] = Field(None, max_length=255)


class FinancialAllocationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_id: int
    financial_entry_id: int
    chart_account_id: Optional[int] = None
    cost_center_id: Optional[int] = None
    activity_id: Optional[int] = None
    process_instance_id: Optional[int] = None
    routine_id: Optional[int] = None
    allocation_type: str = Field(..., pattern=_choices_pattern(ALLOCATION_TYPE_VALUES))
    percentage: Optional[Decimal] = Field(None, ge=0)
    allocated_amount: Optional[Decimal] = None
    notes: Optional[str] = None
    metadata_json: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_allocation(self):
        if self.allocation_type == "percentage" and self.percentage is None:
            raise ValueError("Rateio percentual exige campo percentage.")
        if self.allocation_type == "amount" and self.allocated_amount is None:
            raise ValueError("Rateio por valor exige campo allocated_amount.")
        return self


class FinancialSettlementComponentInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    component_type: str = Field(..., pattern=_choices_pattern(SETTLEMENT_COMPONENT_TYPE_VALUES))
    amount: Decimal = Field(..., ge=0)
    competence_date: Optional[date] = None
    due_date: Optional[date] = None
    source: str = Field("system", min_length=3, max_length=20)
    origin_adjustment_id: Optional[int] = None
    metadata_json: Dict[str, Any] = Field(default_factory=dict)


class FinancialSettlementInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_id: int
    financial_entry_id: int
    settlement_code: str = Field(..., min_length=3, max_length=50)
    settlement_type: str = Field(..., pattern=_choices_pattern(SETTLEMENT_TYPE_VALUES))
    settlement_status: str = Field("posted", pattern=_choices_pattern(SETTLEMENT_STATUS_VALUES))
    settlement_date: date
    bank_account_id: Optional[int] = None
    principal_amount: Decimal = Field(default=Decimal("0"), ge=0)
    interest_amount: Decimal = Field(default=Decimal("0"), ge=0)
    penalty_amount: Decimal = Field(default=Decimal("0"), ge=0)
    discount_amount: Decimal = Field(default=Decimal("0"), ge=0)
    fee_amount: Decimal = Field(default=Decimal("0"), ge=0)
    other_adjustments_amount: Decimal = Field(default=Decimal("0"), ge=0)
    gross_amount: Optional[Decimal] = Field(default=None, ge=0)
    net_amount: Optional[Decimal] = Field(default=None, ge=0)
    settlement_components: List[FinancialSettlementComponentInput] = Field(default_factory=list)
    external_reference: Optional[str] = Field(None, max_length=120)
    import_batch_id: Optional[int] = None
    reconciliation_status: str = Field("pending", pattern=_choices_pattern(RECONCILIATION_STATUS_VALUES))
    notes: Optional[str] = None
    metadata_json: Dict[str, Any] = Field(default_factory=dict)
    created_by_user_id: Optional[int] = None
    created_by_employee_id: Optional[int] = None
    created_by_agent: Optional[str] = Field(None, max_length=50)

    @model_validator(mode="after")
    def calculate_amounts(self):
        expected_net = (
            self.principal_amount
            + self.interest_amount
            + self.penalty_amount
            + self.fee_amount
            + self.other_adjustments_amount
            - self.discount_amount
        )
        if self.net_amount is None:
            self.net_amount = expected_net
        elif self.net_amount != expected_net:
            raise ValueError("net_amount inconsistente com a composição da baixa.")

        if self.gross_amount is None:
            self.gross_amount = expected_net

        if self.settlement_components:
            component_total = Decimal("0")
            for component in self.settlement_components:
                signed_amount = component.amount * (Decimal("-1") if component.component_type == "discount" else Decimal("1"))
                component_total += signed_amount
            if self.gross_amount != component_total:
                raise ValueError("gross_amount inconsistente com a soma dos componentes da baixa.")
        elif self.gross_amount != expected_net:
            raise ValueError("gross_amount inconsistente com a composição agregada da baixa.")

        return self


class FinancialBorderoItemInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    financial_schedule_id: int
    selected_amount: Optional[Decimal] = Field(None, ge=0)
    notes: Optional[str] = None
    metadata_json: Dict[str, Any] = Field(default_factory=dict)


class FinancialBorderoCreateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_id: int
    bordero_type: str = Field(..., pattern=_choices_pattern(BORDERO_TYPE_VALUES))
    name: Optional[str] = Field(None, min_length=2, max_length=160)
    description: Optional[str] = Field(None, max_length=255)
    created_date: Optional[date] = None
    items: List[FinancialBorderoItemInput] = Field(default_factory=list, min_length=1)
    created_by_user_id: Optional[int] = None
    created_by_employee_id: Optional[int] = None
    created_by_agent: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = None
    metadata_json: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def ensure_name(self):
        fallback = _normalize_text(self.name) or _normalize_text(self.description) or _normalize_text(self.notes)
        if not fallback:
            raise ValueError("Campo name é obrigatório ou deve haver descrição/observação para gerar o nome do borderô.")
        self.name = fallback[:160]
        if not _normalize_text(self.description):
            self.description = (_normalize_text(self.notes) or self.name)[:255]
        if not _normalize_text(self.notes):
            self.notes = self.description
        return self


class FinancialBorderoUpdateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = Field(None, min_length=2, max_length=160)
    description: Optional[str] = Field(None, max_length=255)
    created_date: Optional[date] = None
    notes: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None


class FinancialBorderoSettlementInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_id: int
    settlement_date: date
    gross_amount: Decimal = Field(..., gt=0)
    settlement_status: str = Field("posted", pattern=_choices_pattern(BORDERO_SETTLEMENT_STATUS_VALUES))
    bank_account_id: Optional[int] = None
    notes: Optional[str] = None
    metadata_json: Dict[str, Any] = Field(default_factory=dict)
    created_by_user_id: Optional[int] = None
    created_by_employee_id: Optional[int] = None
    created_by_agent: Optional[str] = Field(None, max_length=50)


class FinancialBorderoSettlementUpdateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    settlement_date: Optional[date] = None
    gross_amount: Optional[Decimal] = Field(None, gt=0)
    settlement_status: Optional[str] = Field(None, pattern=_choices_pattern(BORDERO_SETTLEMENT_STATUS_VALUES))
    bank_account_id: Optional[int] = None
    notes: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None
    created_by_user_id: Optional[int] = None
    created_by_employee_id: Optional[int] = None
    created_by_agent: Optional[str] = Field(None, max_length=50)


class FinancialAllocationBatchInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_id: int
    financial_entry_id: int
    allocations: List[FinancialAllocationInput] = Field(default_factory=list)


class FinancialDirectEntryAllocationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chart_account_id: Optional[int] = None
    cost_center_id: Optional[int] = None
    budget_version_id: Optional[int] = None
    budget_line_id: Optional[int] = None
    budget_contract_id: Optional[int] = None
    budget_document_id: Optional[int] = None
    domain_type: Optional[str] = Field(None, pattern=_choices_pattern(DOMAIN_ENABLEMENT_TYPE_VALUES))
    domain_source_kind: Optional[str] = Field("routine", pattern=_choices_pattern(DOMAIN_SOURCE_KIND_VALUES))
    domain_source_id: Optional[int] = None
    domain_label: Optional[str] = Field(None, max_length=255)
    allocation_type: str = Field(..., pattern=_choices_pattern(ALLOCATION_TYPE_VALUES))
    percentage: Optional[Decimal] = Field(None, ge=0)
    allocated_amount: Optional[Decimal] = None
    notes: Optional[str] = None
    metadata_json: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_allocation(self):
        if self.allocation_type == "percentage" and self.percentage is None:
            raise ValueError("Rateio percentual exige campo percentage.")
        if self.allocation_type == "amount" and self.allocated_amount is None:
            raise ValueError("Rateio por valor exige campo allocated_amount.")
        return self


class FinancialDirectEntryCreateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_id: int
    entry_type: str = Field(..., pattern="^(payable|receivable)$")
    description: str = Field(..., min_length=3, max_length=255)
    document_number: Optional[str] = Field(None, max_length=80)
    counterparty_id: int
    bank_account_id: Optional[int] = None
    competence_date: date
    occurred_on: date
    due_date: Optional[date] = None
    original_amount: Decimal = Field(..., gt=0)
    notes: Optional[str] = None
    correction_index_id: Optional[int] = None
    discount_rule_id: Optional[int] = None
    chart_account_id: Optional[int] = None
    cost_center_id: Optional[int] = None
    budget_line_id: Optional[int] = None
    budget_contract_id: Optional[int] = None
    budget_document_id: Optional[int] = None
    allocations: List[FinancialDirectEntryAllocationInput] = Field(default_factory=list)
    metadata_json: Dict[str, Any] = Field(default_factory=dict)
    created_by_user_id: Optional[int] = None
    created_by_employee_id: Optional[int] = None
    created_by_agent: Optional[str] = Field(None, max_length=50)
