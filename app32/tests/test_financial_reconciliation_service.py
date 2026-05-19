import os
import sys
from types import SimpleNamespace

from flask import Flask

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import api.resources.financial as financial_resource_module
import services.financial_reconciliation_service as reconciliation_module
from services.financial_reconciliation_service import FinancialReconciliationService


class _Column:
    def __eq__(self, other):
        return self

    def is_(self, other):
        return self

    def in_(self, other):
        return self

    def asc(self):
        return self


class _QueueQuery:
    def __init__(self, first_results=None, all_results=None):
        self._first_results = list(first_results or [])
        self._all_results = list(all_results or [])

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def first(self):
        if self._first_results:
            return self._first_results.pop(0)
        return None

    def all(self):
        return list(self._all_results)


def test_manually_match_row_supports_multiple_entries(monkeypatch):
    row = SimpleNamespace(
        id=61,
        company_id=9,
        import_batch_id=301,
        amount=200,
        row_number=4,
        movement_nature="credit",
        occurred_on=None,
        due_date=None,
        matched_entry_id=None,
        processing_status="validated",
        error_message=None,
    )
    batch = SimpleNamespace(id=301, company_id=9)
    entry_a = SimpleNamespace(id=11, company_id=9)
    entry_b = SimpleNamespace(id=12, company_id=9)

    class _RowModel:
        id = _Column()
        company_id = _Column()
        deleted_at = _Column()
        query = _QueueQuery(first_results=[row])

    class _BatchModel:
        id = _Column()
        company_id = _Column()
        deleted_at = _Column()
        query = _QueueQuery(first_results=[batch])

    class _EntryModel:
        id = _Column()
        company_id = _Column()
        deleted_at = _Column()
        query = _QueueQuery(first_results=[entry_a, entry_b])

    class _MatchModel:
        company_id = _Column()
        import_row_id = _Column()
        financial_entry_id = _Column()
        deleted_at = _Column()
        query = _QueueQuery(first_results=[None, None])

        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)
            self.id = kwargs.get("financial_entry_id") + 700

    review_calls = []

    monkeypatch.setattr(reconciliation_module.FinancialService, "_ensure_company_scope", lambda *args, **kwargs: None)
    monkeypatch.setattr(reconciliation_module, "FinancialImportRow", _RowModel)
    monkeypatch.setattr(reconciliation_module, "FinancialImportBatch", _BatchModel)
    monkeypatch.setattr(reconciliation_module, "FinancialEntry", _EntryModel)
    monkeypatch.setattr(reconciliation_module, "FinancialReconciliationMatch", _MatchModel)
    monkeypatch.setattr(reconciliation_module.FinancialReconciliationService, "_resolve_row_context", lambda *args, **kwargs: {})
    monkeypatch.setattr(reconciliation_module.FinancialReconciliationService, "_score_match", lambda *args, **kwargs: (0.91, "valor exato"))
    monkeypatch.setattr(
        reconciliation_module.FinancialReconciliationService,
        "_get_remaining_principal",
        lambda entry: 120 if entry.id == 11 else 150,
    )
    monkeypatch.setattr(reconciliation_module.db.session, "add", lambda *args, **kwargs: None)
    monkeypatch.setattr(reconciliation_module.db.session, "flush", lambda: None)
    monkeypatch.setattr(reconciliation_module.db.session, "commit", lambda: None)
    monkeypatch.setattr(
        reconciliation_module.FinancialReconciliationService,
        "review_match",
        lambda **kwargs: (
            review_calls.append(kwargs) or {
                "id": kwargs["match_id"],
                "selected_entry_id": kwargs["selected_entry_id"],
                "principal_amount": float(kwargs["adjustments"]["principal_amount"]),
            },
            None,
        ),
    )

    result, error = FinancialReconciliationService.manually_match_row(
        row_id=61,
        financial_entry_id=11,
        financial_entry_ids=[12],
        company_id=9,
        adjustments={},
        allowed_company_ids=[9],
    )

    assert error is None
    assert result["match_mode"] == "1:N"
    assert result["remaining_row_amount"] == 0
    assert row.matched_entry_id == 11
    assert len(review_calls) == 2
    assert float(review_calls[0]["adjustments"]["principal_amount"]) == 120.0
    assert float(review_calls[1]["adjustments"]["principal_amount"]) == 80.0


def test_row_match_resource_accepts_multiple_entries(monkeypatch):
    app = Flask(__name__)
    captured = {}

    monkeypatch.setattr(financial_resource_module, "get_request_company_id", lambda: 9)
    monkeypatch.setattr(financial_resource_module, "get_accessible_company_ids", lambda: [9])
    monkeypatch.setattr(
        financial_resource_module.FinancialReconciliationService,
        "manually_match_row",
        lambda **kwargs: (captured.setdefault("kwargs", kwargs) or {"ok": True}, None),
    )

    with app.test_request_context(
        "/api/financial/reconciliation/rows/61/match?company_id=9",
        method="POST",
        json={
            "financial_entry_id": 11,
            "financial_entry_ids": [12, 13],
            "allocations": [
                {"financial_entry_id": 11, "principal_amount": 120},
                {"financial_entry_id": 12, "principal_amount": 80},
            ],
        },
    ):
        resource = financial_resource_module.FinancialBankReconciliationRowMatchResource()
        response, status_code = resource.post.__wrapped__(resource, 61)

    assert status_code == 200
    assert captured["kwargs"]["financial_entry_ids"] == [12, 13]
    assert len(captured["kwargs"]["adjustments"]["allocations"]) == 2


def test_row_match_resource_delete_cancels_reconciliation(monkeypatch):
    app = Flask(__name__)
    captured = {}

    monkeypatch.setattr(financial_resource_module, "get_request_company_id", lambda: 9)
    monkeypatch.setattr(financial_resource_module, "get_accessible_company_ids", lambda: [9])
    monkeypatch.setattr(
        financial_resource_module.FinancialReconciliationService,
        "cancel_row_reconciliation",
        lambda **kwargs: (captured.setdefault("kwargs", kwargs) or {"ok": True}, None),
    )

    with app.test_request_context(
        "/api/financial/reconciliation/rows/61/match?company_id=9",
        method="DELETE",
        json={"reason": "Ajuste operacional"},
    ):
        resource = financial_resource_module.FinancialBankReconciliationRowMatchResource()
        response, status_code = resource.delete.__wrapped__(resource, 61)

    assert status_code == 200
    assert captured["kwargs"]["row_id"] == 61
    assert captured["kwargs"]["reason"] == "Ajuste operacional"


def test_reconcile_group_balanced_multiple_rows_and_entries(monkeypatch):
    rows = [
        SimpleNamespace(id=61, company_id=9, import_batch_id=301, amount=50, row_number=1, movement_nature="credit", created_entry_id=None),
        SimpleNamespace(id=62, company_id=9, import_batch_id=301, amount=70, row_number=2, movement_nature="credit", created_entry_id=None),
    ]
    entries = [
        SimpleNamespace(id=11, company_id=9, movement_nature="credit", original_amount=60),
        SimpleNamespace(id=12, company_id=9, movement_nature="credit", original_amount=60),
    ]

    class _RowModel:
        id = _Column()
        company_id = _Column()
        deleted_at = _Column()
        row_number = _Column()
        query = _QueueQuery(all_results=rows)

    class _EntryModel:
        id = _Column()
        company_id = _Column()
        deleted_at = _Column()
        query = _QueueQuery(all_results=entries)

    class _MatchModel:
        company_id = _Column()
        import_row_id = _Column()
        match_status = _Column()
        deleted_at = _Column()
        query = _QueueQuery(first_results=[None])

    manual_calls = []

    monkeypatch.setattr(reconciliation_module.FinancialService, "_ensure_company_scope", lambda *args, **kwargs: None)
    monkeypatch.setattr(reconciliation_module, "FinancialImportRow", _RowModel)
    monkeypatch.setattr(reconciliation_module, "FinancialEntry", _EntryModel)
    monkeypatch.setattr(reconciliation_module, "FinancialReconciliationMatch", _MatchModel)
    monkeypatch.setattr(
        reconciliation_module.FinancialReconciliationService,
        "_get_remaining_principal",
        lambda entry: entry.original_amount,
    )
    monkeypatch.setattr(
        reconciliation_module.FinancialReconciliationService,
        "manually_match_row",
        lambda **kwargs: (manual_calls.append(kwargs) or {"row_id": kwargs["row_id"]}, None),
    )

    result, error = FinancialReconciliationService.reconcile_group(
        company_id=9,
        bank_row_ids=[61, 62],
        financial_entry_ids=[11, 12],
        allowed_company_ids=[9],
    )

    assert error is None
    assert result["match_mode"] == "N:N"
    assert result["requires_resolution"] is False
    assert result["difference"] == 0
    assert len(manual_calls) == 2
    assert manual_calls[0]["adjustments"]["allocations"] == [
        {"financial_entry_id": 11, "principal_amount": 50}
    ]
    assert manual_calls[1]["adjustments"]["allocations"] == [
        {"financial_entry_id": 11, "principal_amount": 10},
        {"financial_entry_id": 12, "principal_amount": 60},
    ]


def test_group_match_resource_returns_resolution_conflict(monkeypatch):
    app = Flask(__name__)
    captured = {}

    monkeypatch.setattr(financial_resource_module, "get_request_company_id", lambda: 9)
    monkeypatch.setattr(financial_resource_module, "get_accessible_company_ids", lambda: [9])
    def _fake_reconcile_group(**kwargs):
        captured["kwargs"] = kwargs
        return {
            "requires_resolution": True,
            "difference": 10,
            "can_create_complement": True,
        }, None

    monkeypatch.setattr(
        financial_resource_module.FinancialReconciliationService,
        "reconcile_group",
        _fake_reconcile_group,
    )

    with app.test_request_context(
        "/api/financial/reconciliation/groups/match?company_id=9",
        method="POST",
        json={"bank_row_ids": [61, 62], "financial_entry_ids": [11]},
    ):
        resource = financial_resource_module.FinancialBankReconciliationGroupMatchResource()
        response, status_code = resource.post.__wrapped__(resource)

    assert status_code == 409
    assert response["requires_resolution"] is True
    assert captured["kwargs"]["bank_row_ids"] == [61, 62]
