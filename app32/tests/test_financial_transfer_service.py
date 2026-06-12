import os
import sys
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import services.financial_transfer_service as transfer_module
from services.financial_transfer_service import FinancialTransferService


class _Column:
    def __eq__(self, other):
        return ("eq", other)

    def is_(self, other):
        return ("is", other)


class _EmptyQuery:
    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return None


def test_create_transfer_generates_entries_and_settlements(monkeypatch):
    created_entry_payloads = []
    created_settlement_payloads = []

    monkeypatch.setattr(transfer_module.FinancialService, "_ensure_company_scope", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        transfer_module.FinancialTransferService,
        "_load_account",
        lambda **kwargs: (
            SimpleNamespace(id=11, name="Conta Origem")
            if kwargs["bank_account_id"] == 11
            else SimpleNamespace(id=22, name="Conta Destino")
        ),
    )
    monkeypatch.setattr(
        transfer_module.FinancialService,
        "create_entry",
        lambda *, payload, allowed_company_ids=None: (
            created_entry_payloads.append(dict(payload)) or SimpleNamespace(id=len(created_entry_payloads), original_amount=payload["original_amount"]),
            None,
        ),
    )
    monkeypatch.setattr(
        transfer_module.FinancialService,
        "create_settlement",
        lambda *, payload, allowed_company_ids=None: (
            created_settlement_payloads.append(dict(payload)) or SimpleNamespace(id=len(created_settlement_payloads), settlement_code=payload["settlement_code"], to_dict=lambda: dict(payload)),
            None,
        ),
    )
    monkeypatch.setattr(
        transfer_module.FinancialService,
        "serialize_entry",
        lambda entry, include_children=False: {"id": entry.id},
    )

    payload = {
        "company_id": 7,
        "source_bank_account_id": 11,
        "destination_bank_account_id": 22,
        "occurred_on": "2026-05-09",
        "description": "Transferência operacional",
        "original_amount": "420.00",
        "document_number": "TRF-420",
    }

    result, error = FinancialTransferService.create_transfer(payload=payload, allowed_company_ids=[7])

    assert error is None
    assert result is not None
    assert len(created_entry_payloads) == 2
    assert len(created_settlement_payloads) == 2
    assert created_settlement_payloads[0]["bank_account_id"] == 11
    assert created_settlement_payloads[1]["bank_account_id"] == 22
    assert created_settlement_payloads[0]["principal_amount"] == Decimal("420.00")
    assert created_settlement_payloads[1]["principal_amount"] == Decimal("420.00")
    assert result["summary"]["source_settlement_code"].endswith("-out-stl")
    assert result["summary"]["destination_settlement_code"].endswith("-in-stl")


def test_reconciliation_auto_settlement_inherits_bank_account_from_bank_row(monkeypatch):
    row = SimpleNamespace(
        id=91,
        amount=Decimal("300.00"),
        occurred_on=date(2026, 5, 6),
        due_date=None,
        normalized_payload={"bank_account_id": 33},
    )
    entry = SimpleNamespace(
        id=501,
        due_date=None,
        competence_date=None,
        bank_account_id=None,
    )
    match = SimpleNamespace(id=801, import_batch_id=77)
    captured = {}

    monkeypatch.setattr(
        transfer_module,
        "FinancialTransferService",
        transfer_module.FinancialTransferService,
    )

    import services.financial_reconciliation_service as reconciliation_module

    monkeypatch.setattr(reconciliation_module.FinancialReconciliationService, "_get_remaining_principal", lambda entry: Decimal("300.00"))

    def _fake_create_settlement(*, payload):
        captured["payload"] = dict(payload)
        return SimpleNamespace(to_dict=lambda: dict(payload)), None

    monkeypatch.setattr(
        reconciliation_module.FinancialService,
        "create_settlement",
        _fake_create_settlement,
    )
    monkeypatch.setattr(reconciliation_module.FinancialService, "set_entry_reconciliation_state", lambda **kwargs: None)
    monkeypatch.setattr(
        reconciliation_module,
        "FinancialSettlement",
        type(
            "FinancialSettlementStub",
            (),
            {
                "company_id": _Column(),
                "financial_entry_id": _Column(),
                "external_reference": _Column(),
                "deleted_at": _Column(),
                "query": _EmptyQuery(),
            },
        ),
    )

    settlement, error = reconciliation_module.FinancialReconciliationService._create_auto_settlement_from_match(
        company_id=7,
        row=row,
        entry=entry,
        match=match,
        adjustments={"principal_amount": Decimal("300.00")},
    )

    assert error is None
    assert settlement is not None
    assert captured["payload"]["bank_account_id"] == 33
