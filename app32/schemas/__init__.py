"""
Schemas package for APP32.
Contains Marshmallow schemas for serialization/deserialization.
"""

from flask_marshmallow import Marshmallow

ma = Marshmallow()

# Import schemas here
from .company import CompanySchema, company_schema, companies_schema
from .indicator import indicator_schema, indicators_schema, indicator_group_schema, indicator_groups_schema
from .occurrence import occurrence_schema, occurrences_schema
from .financial import (
    FinancialEntrySchema,
    FinancialEntryAllocationSchema,
    FinancialSettlementSchema,
    FinancialImportBatchInput,
    FinancialImportRowInput,
    financial_entry_schema,
    financial_entries_schema,
    financial_entry_allocation_schema,
    financial_entry_allocations_schema,
    financial_settlement_schema,
    financial_settlements_schema,
)
from .financial_budget import (
    FinancialBudgetVersionSchema,
    FinancialBudgetLineSchema,
    FinancialBudgetAmountSchema,
    FinancialBudgetVersionInput,
    FinancialBudgetVersionUpdateInput,
    FinancialBudgetMatrixUpsertInput,
    financial_budget_version_schema,
    financial_budget_versions_schema,
    financial_budget_line_schema,
    financial_budget_lines_schema,
    financial_budget_amount_schema,
    financial_budget_amounts_schema,
)

__all__ = [
    'ma', 'CompanySchema', 'company_schema', 'companies_schema',
    'indicator_schema', 'indicators_schema', 'indicator_group_schema', 'indicator_groups_schema',
    'occurrence_schema', 'occurrences_schema',
    'FinancialEntrySchema', 'FinancialEntryAllocationSchema', 'FinancialSettlementSchema',
    'FinancialImportBatchInput', 'FinancialImportRowInput',
    'financial_entry_schema', 'financial_entries_schema',
    'financial_entry_allocation_schema', 'financial_entry_allocations_schema',
    'financial_settlement_schema', 'financial_settlements_schema',
    'FinancialBudgetVersionSchema', 'FinancialBudgetLineSchema', 'FinancialBudgetAmountSchema',
    'FinancialBudgetVersionInput', 'FinancialBudgetVersionUpdateInput', 'FinancialBudgetMatrixUpsertInput',
    'financial_budget_version_schema', 'financial_budget_versions_schema',
    'financial_budget_line_schema', 'financial_budget_lines_schema',
    'financial_budget_amount_schema', 'financial_budget_amounts_schema',
]
