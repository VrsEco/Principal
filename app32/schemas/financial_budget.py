from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional

from marshmallow import fields
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from models import (
    FinancialBudgetAmount,
    FinancialBudgetContract,
    FinancialBudgetDocument,
    FinancialBudgetLine,
    FinancialBudgetVersion,
)
from models.financial import MOVEMENT_NATURE_VALUES
from models.financial_budget import (
    BUDGET_CONTRACT_STATUS_VALUES,
    BUDGET_DOCUMENT_STATUS_VALUES,
    BUDGET_DOCUMENT_TYPE_VALUES,
    BUDGET_LINE_VIEW_VALUES,
    BUDGET_VERSION_SCENARIO_VALUES,
    BUDGET_VERSION_STATUS_VALUES,
)
from schemas import ma


def _choices_pattern(values: tuple[str, ...]) -> str:
    return "^(" + "|".join(values) + ")$"


def _strip_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


class FinancialBudgetVersionSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = FinancialBudgetVersion
        load_instance = True
        include_fk = True

    created_at = fields.String(dump_only=True)
    updated_at = fields.String(dump_only=True)


class FinancialBudgetLineSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = FinancialBudgetLine
        load_instance = True
        include_fk = True

    planned_amount = fields.Float()
    created_at = fields.String(dump_only=True)
    updated_at = fields.String(dump_only=True)


class FinancialBudgetAmountSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = FinancialBudgetAmount
        load_instance = True
        include_fk = True

    budget_amount = fields.Float()
    created_at = fields.String(dump_only=True)
    updated_at = fields.String(dump_only=True)


class FinancialBudgetContractSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = FinancialBudgetContract
        load_instance = True
        include_fk = True

    contract_amount = fields.Float()
    created_at = fields.String(dump_only=True)
    updated_at = fields.String(dump_only=True)


class FinancialBudgetDocumentSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = FinancialBudgetDocument
        load_instance = True
        include_fk = True

    document_amount = fields.Float()
    created_at = fields.String(dump_only=True)
    updated_at = fields.String(dump_only=True)


financial_budget_version_schema = FinancialBudgetVersionSchema()
financial_budget_versions_schema = FinancialBudgetVersionSchema(many=True)
financial_budget_line_schema = FinancialBudgetLineSchema()
financial_budget_lines_schema = FinancialBudgetLineSchema(many=True)
financial_budget_amount_schema = FinancialBudgetAmountSchema()
financial_budget_amounts_schema = FinancialBudgetAmountSchema(many=True)
financial_budget_contract_schema = FinancialBudgetContractSchema()
financial_budget_contracts_schema = FinancialBudgetContractSchema(many=True)
financial_budget_document_schema = FinancialBudgetDocumentSchema()
financial_budget_documents_schema = FinancialBudgetDocumentSchema(many=True)


class FinancialBudgetVersionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_id: int
    code: str = Field(..., min_length=2, max_length=50)
    name: str = Field(..., min_length=3, max_length=160)
    scenario_type: str = Field("original", pattern=_choices_pattern(BUDGET_VERSION_SCENARIO_VALUES))
    status: str = Field("draft", pattern=_choices_pattern(BUDGET_VERSION_STATUS_VALUES))
    period_start: date
    period_end: date
    notes: Optional[str] = None
    metadata_json: Dict[str, Any] = Field(default_factory=dict)
    created_by_user_id: Optional[int] = None

    @field_validator("code", "name", "notes", mode="before")
    @classmethod
    def normalize_text(cls, value):
        return _strip_text(value)

    @model_validator(mode="after")
    def validate_period(self):
        if self.period_end < self.period_start:
            raise ValueError("period_end deve ser maior ou igual a period_start.")
        return self


class FinancialBudgetVersionUpdateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: Optional[str] = Field(None, min_length=2, max_length=50)
    name: Optional[str] = Field(None, min_length=3, max_length=160)
    scenario_type: Optional[str] = Field(None, pattern=_choices_pattern(BUDGET_VERSION_SCENARIO_VALUES))
    status: Optional[str] = Field(None, pattern=_choices_pattern(BUDGET_VERSION_STATUS_VALUES))
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    notes: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None
    approved_by_user_id: Optional[int] = None

    @field_validator("code", "name", "notes", mode="before")
    @classmethod
    def normalize_text(cls, value):
        return _strip_text(value)


class FinancialBudgetVersionDuplicateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_id: int
    code: Optional[str] = Field(None, min_length=2, max_length=50)
    name: Optional[str] = Field(None, min_length=3, max_length=160)
    scenario_type: Optional[str] = Field(None, pattern=_choices_pattern(BUDGET_VERSION_SCENARIO_VALUES))
    status: str = Field("draft", pattern=_choices_pattern(BUDGET_VERSION_STATUS_VALUES))
    notes: Optional[str] = None
    created_by_user_id: Optional[int] = None

    @field_validator("code", "name", "notes", mode="before")
    @classmethod
    def normalize_text(cls, value):
        return _strip_text(value)


class FinancialBudgetMatrixValueInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    period_month: date
    budget_amount: Decimal = Field(..., ge=0)
    notes: Optional[str] = None
    metadata_json: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("notes", mode="before")
    @classmethod
    def normalize_notes(cls, value):
        return _strip_text(value)


class FinancialBudgetMatrixLineInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: Optional[int] = None
    line_code: str = Field(..., min_length=1, max_length=60)
    line_name: str = Field(..., min_length=2, max_length=160)
    budget_view: str = Field("competence", pattern=_choices_pattern(BUDGET_LINE_VIEW_VALUES))
    movement_nature: str = Field("debit", pattern=_choices_pattern(MOVEMENT_NATURE_VALUES))
    line_order: int = Field(100, ge=0)
    planned_amount: Decimal = Field(default=Decimal("0"), ge=0)
    chart_account_id: Optional[int] = None
    cost_center_id: Optional[int] = None
    activity_id: Optional[int] = None
    process_instance_id: Optional[int] = None
    routine_id: Optional[int] = None
    is_active: bool = True
    notes: Optional[str] = None
    metadata_json: Dict[str, Any] = Field(default_factory=dict)
    amounts: List[FinancialBudgetMatrixValueInput] = Field(default_factory=list)

    @field_validator("line_code", "line_name", "notes", mode="before")
    @classmethod
    def normalize_text(cls, value):
        return _strip_text(value)


class FinancialBudgetMatrixUpsertInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_id: int
    version_id: int
    lines: List[FinancialBudgetMatrixLineInput] = Field(default_factory=list)


class FinancialBudgetVersionCreate(FinancialBudgetVersionInput):
    pass


class FinancialBudgetVersionUpdate(FinancialBudgetVersionUpdateInput):
    pass


class FinancialBudgetLineCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_id: int
    budget_version_id: int
    line_code: str = Field(..., min_length=1, max_length=60)
    line_name: str = Field(..., min_length=2, max_length=160)
    budget_view: str = Field("competence", pattern=_choices_pattern(BUDGET_LINE_VIEW_VALUES))
    movement_nature: str = Field("debit", pattern=_choices_pattern(MOVEMENT_NATURE_VALUES))
    line_order: int = Field(100, ge=0)
    planned_amount: Decimal = Field(default=Decimal("0"), ge=0)
    chart_account_id: Optional[int] = None
    cost_center_id: Optional[int] = None
    activity_id: Optional[int] = None
    process_instance_id: Optional[int] = None
    routine_id: Optional[int] = None
    notes: Optional[str] = None
    is_active: bool = True
    metadata_json: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("line_code", "line_name", "notes", mode="before")
    @classmethod
    def normalize_text(cls, value):
        return _strip_text(value)


class FinancialBudgetLineUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    line_code: Optional[str] = Field(None, min_length=1, max_length=60)
    line_name: Optional[str] = Field(None, min_length=2, max_length=160)
    budget_view: Optional[str] = Field(None, pattern=_choices_pattern(BUDGET_LINE_VIEW_VALUES))
    movement_nature: Optional[str] = Field(None, pattern=_choices_pattern(MOVEMENT_NATURE_VALUES))
    line_order: Optional[int] = Field(None, ge=0)
    planned_amount: Optional[Decimal] = Field(None, ge=0)
    chart_account_id: Optional[int] = None
    cost_center_id: Optional[int] = None
    activity_id: Optional[int] = None
    process_instance_id: Optional[int] = None
    routine_id: Optional[int] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None
    metadata_json: Optional[Dict[str, Any]] = None

    @field_validator("line_code", "line_name", "notes", mode="before")
    @classmethod
    def normalize_text(cls, value):
        return _strip_text(value)


class FinancialBudgetAmountUpsert(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_id: int
    budget_line_id: int
    period_month: date
    budget_amount: Decimal = Field(..., ge=0)
    notes: Optional[str] = None
    metadata_json: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("notes", mode="before")
    @classmethod
    def normalize_notes(cls, value):
        return _strip_text(value)


class FinancialBudgetContractCreateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_id: int
    budget_line_id: int
    contract_code: str = Field(..., min_length=2, max_length=60)
    name: str = Field(..., min_length=3, max_length=160)
    status: str = Field("draft", pattern=_choices_pattern(BUDGET_CONTRACT_STATUS_VALUES))
    contract_amount: Decimal = Field(..., ge=0)
    counterparty_id: Optional[int] = None
    signed_at: Optional[date] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    notes: Optional[str] = None
    metadata_json: Dict[str, Any] = Field(default_factory=dict)
    created_by_user_id: Optional[int] = None

    @field_validator("contract_code", "name", "notes", mode="before")
    @classmethod
    def normalize_text(cls, value):
        return _strip_text(value)


class FinancialBudgetContractUpdateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_code: Optional[str] = Field(None, min_length=2, max_length=60)
    name: Optional[str] = Field(None, min_length=3, max_length=160)
    status: Optional[str] = Field(None, pattern=_choices_pattern(BUDGET_CONTRACT_STATUS_VALUES))
    contract_amount: Optional[Decimal] = Field(None, ge=0)
    counterparty_id: Optional[int] = None
    signed_at: Optional[date] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    notes: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None

    @field_validator("contract_code", "name", "notes", mode="before")
    @classmethod
    def normalize_text(cls, value):
        return _strip_text(value)


class FinancialBudgetDocumentCreateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_id: int
    budget_contract_id: int
    document_code: str = Field(..., min_length=2, max_length=60)
    title: str = Field(..., min_length=3, max_length=160)
    document_type: str = Field("invoice", pattern=_choices_pattern(BUDGET_DOCUMENT_TYPE_VALUES))
    status: str = Field("registered", pattern=_choices_pattern(BUDGET_DOCUMENT_STATUS_VALUES))
    document_number: Optional[str] = Field(None, max_length=80)
    document_amount: Decimal = Field(..., ge=0)
    issue_date: Optional[date] = None
    competence_date: Optional[date] = None
    counterparty_id: Optional[int] = None
    notes: Optional[str] = None
    metadata_json: Dict[str, Any] = Field(default_factory=dict)
    created_by_user_id: Optional[int] = None

    @field_validator("document_code", "title", "document_number", "notes", mode="before")
    @classmethod
    def normalize_text(cls, value):
        return _strip_text(value)


class FinancialBudgetDocumentUpdateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_code: Optional[str] = Field(None, min_length=2, max_length=60)
    title: Optional[str] = Field(None, min_length=3, max_length=160)
    document_type: Optional[str] = Field(None, pattern=_choices_pattern(BUDGET_DOCUMENT_TYPE_VALUES))
    status: Optional[str] = Field(None, pattern=_choices_pattern(BUDGET_DOCUMENT_STATUS_VALUES))
    document_number: Optional[str] = Field(None, max_length=80)
    document_amount: Optional[Decimal] = Field(None, ge=0)
    issue_date: Optional[date] = None
    competence_date: Optional[date] = None
    counterparty_id: Optional[int] = None
    notes: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None

    @field_validator("document_code", "title", "document_number", "notes", mode="before")
    @classmethod
    def normalize_text(cls, value):
        return _strip_text(value)


class FinancialBudgetDocumentScheduleInstallmentInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    due_date: date
    amount: Decimal = Field(..., gt=0)
    label: Optional[str] = Field(None, min_length=1, max_length=80)
    competence_date: Optional[date] = None

    @field_validator("label", mode="before")
    @classmethod
    def normalize_text(cls, value):
        return _strip_text(value)


class FinancialBudgetDocumentScheduleBatchInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_id: int
    installments: List[FinancialBudgetDocumentScheduleInstallmentInput] = Field(default_factory=list)
    auto_post: bool = False
    notes: Optional[str] = None

    @field_validator("notes", mode="before")
    @classmethod
    def normalize_text(cls, value):
        return _strip_text(value)

    @model_validator(mode="after")
    def validate_installments(self):
        if not self.installments:
            raise ValueError("Informe ao menos uma parcela para gerar os agendamentos.")
        return self
