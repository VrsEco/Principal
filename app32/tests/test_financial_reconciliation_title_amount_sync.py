from decimal import Decimal
from types import SimpleNamespace

from services.financial_reconciliation_service import FinancialReconciliationService
from services.financial_service import FinancialService


def test_sync_updates_schedule_template_metadata_used_as_principal_basis():
    entry = SimpleNamespace(
        original_amount=Decimal("300.00"),
        metadata_json={"schedule_template_amount": 300.0},
    )

    entry.original_amount = Decimal("350.00")
    FinancialReconciliationService._sync_entry_schedule_template_amount(entry, Decimal("350.00"))

    assert FinancialService._resolve_entry_principal_basis_amount(entry) == Decimal("350.00")


def test_sync_ignores_entries_without_schedule_template_metadata():
    entry = SimpleNamespace(original_amount=Decimal("300.00"), metadata_json={"x": 1})

    FinancialReconciliationService._sync_entry_schedule_template_amount(entry, Decimal("350.00"))

    assert entry.metadata_json == {"x": 1}
