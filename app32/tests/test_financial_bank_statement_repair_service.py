import os
import sys
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import services.financial_bank_statement_repair_service as repair_module
from services.financial_bank_statement_repair_service import FinancialBankStatementRepairService


class _Column:
    def __eq__(self, other):
        return ("eq", other)

    def __ne__(self, other):
        return ("ne", other)

    def is_(self, other):
        return ("is", other)

    def asc(self):
        return self


class _Query:
    def __init__(self, items):
        self.items = list(items)

    def filter(self, *args, **kwargs):
        return self

    def join(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def limit(self, value):
        self.items = self.items[:value]
        return self

    def all(self):
        return list(self.items)

    def first(self):
        return self.items[0] if self.items else None


class _Session:
    def __init__(self, pairs):
        self.pairs = pairs
        self.committed = False
        self.rolled_back = False

    def query(self, *args, **kwargs):
        return _Query(self.pairs)

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True


def test_repair_reconciliation_bank_account_uses_import_row(monkeypatch):
    settlement = SimpleNamespace(
        id=10,
        financial_entry_id=20,
        bank_account_id=None,
        external_reference="reconciliation-match:99",
        metadata_json={"import_row_id": 30, "mode": "auto_settlement_from_reconciliation"},
    )
    entry = SimpleNamespace(id=20, bank_account_id=None)
    row = SimpleNamespace(normalized_payload={"bank_account_id": 44})
    session = _Session([(settlement, entry)])

    monkeypatch.setattr(repair_module, "db", SimpleNamespace(session=session))
    monkeypatch.setattr(
        repair_module,
        "FinancialSettlement",
        type("SettlementModel", (), {"company_id": _Column(), "financial_entry_id": _Column(), "bank_account_id": _Column(), "deleted_at": _Column(), "settlement_status": _Column(), "id": _Column()}),
    )
    monkeypatch.setattr(
        repair_module,
        "FinancialEntry",
        type("EntryModel", (), {"company_id": _Column(), "id": _Column(), "deleted_at": _Column()}),
    )
    monkeypatch.setattr(
        repair_module,
        "FinancialImportRow",
        type("RowModel", (), {"company_id": _Column(), "id": _Column(), "deleted_at": _Column(), "query": _Query([row])}),
    )

    result = FinancialBankStatementRepairService.repair_missing_bank_accounts_from_reconciliation(company_id=7, apply=True)

    assert result["updated"] == 1
    assert settlement.bank_account_id == 44
    assert session.committed is True


def test_backfill_transfer_settlement_builds_payload(monkeypatch):
    entry = SimpleNamespace(
        id=50,
        entry_code="trf-historico-out",
        entry_type="transfer",
        movement_nature="debit",
        status="posted",
        bank_account_id=11,
        original_amount=Decimal("250.00"),
        occurred_on=date(2026, 5, 9),
        due_date=None,
        competence_date=None,
        created_by_user_id=1,
        created_by_employee_id=None,
        created_by_agent="app32",
        metadata_json={
            "is_transfer": True,
            "transfer_group_id": "trf-historico",
            "transfer_direction": "out",
            "counterpart_bank_account_id": 22,
        },
    )
    created = []

    monkeypatch.setattr(
        repair_module,
        "FinancialEntry",
        type("EntryModel", (), {"company_id": _Column(), "deleted_at": _Column(), "entry_type": _Column(), "status": _Column(), "id": _Column(), "query": _Query([entry])}),
    )
    monkeypatch.setattr(
        repair_module,
        "FinancialSettlement",
        type("SettlementModel", (), {"company_id": _Column(), "financial_entry_id": _Column(), "deleted_at": _Column(), "settlement_status": _Column(), "query": _Query([])}),
    )
    monkeypatch.setattr(
        repair_module.FinancialService,
        "create_settlement",
        lambda *, payload, allowed_company_ids=None: (created.append(dict(payload)) or SimpleNamespace(id=1), None),
    )

    result = FinancialBankStatementRepairService.backfill_missing_transfer_settlements(company_id=7, apply=True)

    assert result["created"] == 1
    assert created[0]["financial_entry_id"] == 50
    assert created[0]["bank_account_id"] == 11
    assert created[0]["principal_amount"] == Decimal("250.00")
    assert created[0]["external_reference"] == "transfer:trf-historico:out"
