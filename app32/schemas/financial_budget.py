from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional

from marshmallow import fields
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from models import FinancialBudgetAmount, FinancialBudgetLine, FinancialBudgetVersion
from models.financial import MOVEMENT_NATURE_VALUES
from models.financial_budget import (
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


financial_budget_version_schema = FinancialBudgetVersionSchema()
financial_budget_versions_schema = FinancialBudgetVersionSchema(many=True)
financial_budget_line_schema = FinancialBudgetLineSchema()
financial_budget_lines_schema = FinancialBudgetLineSchema(many=True)
financial_budget_amount_schema = FinancialBudgetAmountSchema()
financial_budget_amounts_schema = FinancialBudgetAmountSchema(many=True)


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


# Contratos operacionais compatíveis com o novo backend do orçamento matricial
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
