from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class FinancialManagementReportFiltersInput(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)

    report_type: str
    period_start: Optional[date] = None
    period_end: Optional[date] = None

    competence_start: Optional[date] = None
    competence_end: Optional[date] = None
    due_start: Optional[date] = None
    due_end: Optional[date] = None
    settlement_start: Optional[date] = None
    settlement_end: Optional[date] = None
    reference_date: Optional[date] = None

    bank_account_id: Optional[int] = Field(default=None, ge=1)
    bank_account_ids: list[int] = Field(default_factory=list)
    chart_account_id: Optional[int] = Field(default=None, ge=1)
    chart_account_ids: list[int] = Field(default_factory=list)
    cost_center_id: Optional[int] = Field(default=None, ge=1)
    cost_center_ids: list[int] = Field(default_factory=list)
    project_ids: list[int] = Field(default_factory=list)
    process_ids: list[int] = Field(default_factory=list)
    working_capital_accounts: list[int] = Field(default_factory=list)
    manual_values: dict[int, Decimal] = Field(default_factory=dict)
    counterparty_id: Optional[int] = Field(default=None, ge=1)
    counterparty_ids: list[int] = Field(default_factory=list)

    movement_nature: Optional[str] = None
    schedule_status: Optional[str] = None
    frequency: Optional[str] = None

    include_projected: bool = False
    include_reconciled_only: bool = False
    include_overdraft: bool = True

    include_open: bool = True
    include_settled: bool = True
    include_partial: bool = True
    include_bordero: bool = True
    include_receivable: bool = True
    include_payable: bool = True
    include_budget_vs_actual: bool = False

    show_code: bool = True
    show_description: bool = True
    show_competence_column: bool = True
    show_due_column: bool = True
    show_liquidation_column: bool = True
    show_title_number: bool = True
    show_installment: bool = True
    show_history: bool = True
    show_counterparty: bool = True
    show_title_amount: bool = True
    show_balance_amount: bool = True
    show_competence_date: bool = True
    show_due_date: bool = True
    show_settlement_date: bool = True
    order_by: Literal[
        'code',
        'description',
        'project',
        'title_number',
        'installment',
        'history',
        'counterparty',
        'title_amount',
        'balance_amount',
        'competence_date',
        'due_date',
        'settlement_date',
    ] = 'code'
    order_direction: Literal['asc', 'desc'] = 'asc'
    orientation: Literal['portrait', 'landscape'] = 'landscape'
    output_mode: Literal['screen', 'pdf'] = 'screen'
