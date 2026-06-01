import os
import sys
import io
from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace

from flask import Flask

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import api.resources.financial as financial_resource_module
import services.financial_reconciliation_service as reconciliation_module
import services.financial_reconciliation_workspace_service as workspace_module
from services.financial_reconciliation_workspace_service import FinancialReconciliationWorkspaceService
from services.financial_reconciliation_service import FinancialReconciliationService


class _Column:
    def __eq__(self, other):
        return ("eq", other)

    def is_(self, other):
        return ("is", other)

    def asc(self):
        return self


class _SingleResultQuery:
    def __init__(self, result):
        self._result = result

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self._result


def test_get_workspace_requires_bank_account():
    result, error = FinancialReconciliationWorkspaceService.get_workspace(
        company_id=1,
        bank_account_id=None,
        allowed_company_ids=[1],
    )

    assert result is None
    assert error == "Conta bancária é obrigatória para abrir a conciliação."


def test_workspace_filters_match_absolute_amount_and_movement_nature():
    assert FinancialReconciliationWorkspaceService._workspace_row_matches_filters(
        {"amount": -150.0, "movement_nature": "debit"},
        amount_filter=Decimal("150.00"),
        movement_nature="debit",
    )
    assert FinancialReconciliationWorkspaceService._workspace_row_matches_filters(
        {"remaining_amount": "150.00", "movement_nature": "credit"},
        amount_filter=Decimal("150.00"),
        movement_nature="credit",
    )
    assert not FinancialReconciliationWorkspaceService._workspace_row_matches_filters(
        {"amount": -150.01, "movement_nature": "debit"},
        amount_filter=Decimal("150.00"),
        movement_nature="debit",
    )
    assert not FinancialReconciliationWorkspaceService._workspace_row_matches_filters(
        {"amount": -150.0, "movement_nature": "credit"},
        amount_filter=Decimal("150.00"),
        movement_nature="debit",
    )


def test_workspace_amount_query_parser_accepts_brl_and_decimal_dot():
    app = Flask(__name__)

    with app.test_request_context("/api/financial/reconciliation/workspace?amount=R$%201.234,56"):
        assert financial_resource_module._get_optional_decimal_arg("amount") == Decimal("1234.56")

    with app.test_request_context("/api/financial/reconciliation/workspace?amount=-100.00"):
        assert financial_resource_module._get_optional_decimal_arg("amount") == Decimal("100.00")


def test_create_entry_from_row_requires_bank_account_link(monkeypatch):
    row = SimpleNamespace(
        id=91,
        company_id=1,
        import_batch_id=12,
        occurred_on=None,
        due_date=None,
        amount=150.0,
        movement_nature="debit",
        description="Tarifa bancária",
        row_number=3,
        document_number=None,
        bank_reference=None,
        normalized_payload={},
    )
    batch = SimpleNamespace(
        id=12,
        company_id=1,
        source_type="csv",
        batch_code="REC-001",
        imported_at=datetime(2026, 3, 28, 10, 0, 0),
    )

    class _FakeImportRowModel:
        id = _Column()
        company_id = _Column()
        deleted_at = _Column()
        query = _SingleResultQuery(row)

    class _FakeImportBatchModel:
        id = _Column()
        company_id = _Column()
        deleted_at = _Column()
        query = _SingleResultQuery(batch)

    monkeypatch.setattr(workspace_module.FinancialService, "_ensure_company_scope", lambda *args, **kwargs: None)
    monkeypatch.setattr(workspace_module, "FinancialImportRow", _FakeImportRowModel)
    monkeypatch.setattr(workspace_module, "FinancialImportBatch", _FakeImportBatchModel)

    result, error = FinancialReconciliationWorkspaceService.create_entry_from_row(
        company_id=1,
        row_id=91,
        payload={"description": "Tarifa bancária"},
        allowed_company_ids=[1],
    )

    assert result is None
    assert error == "A linha do extrato precisa estar vinculada a uma conta bancária para criar o lançamento."


def test_import_batch_resource_runs_auto_match_when_reconciliation_mode_enabled(monkeypatch):
    app = Flask(__name__)
    calls = {}

    monkeypatch.setattr(financial_resource_module, "get_request_company_id", lambda: 7)
    monkeypatch.setattr(financial_resource_module, "get_accessible_company_ids", lambda: [7])
    monkeypatch.setattr(
        financial_resource_module.FinancialImportService,
        "create_import_batch",
        lambda **kwargs: ({"batch": {"id": 55, "batch_code": "REC-055"}}, None),
    )

    def _fake_auto_match_batch(**kwargs):
        calls["kwargs"] = kwargs
        return ({"suggested_count": 4, "unmatched_count": 1}, None)

    monkeypatch.setattr(
        financial_resource_module.FinancialReconciliationService,
        "auto_match_batch",
        _fake_auto_match_batch,
    )

    with app.test_request_context(
        "/api/financial/imports?company_id=7",
        method="POST",
        data={
            "batch_code": "REC-055",
            "source_type": "csv",
            "bank_account_id": "10",
            "integration_channel": "file",
            "reconciliation_mode": "1",
            "file": (io.BytesIO(b"descricao,valor\nTeste,100\n"), "extrato.csv"),
        },
        content_type="multipart/form-data",
    ):
        resource = financial_resource_module.FinancialImportBatchListResource()
        response, status_code = resource.post.__wrapped__(resource)

    assert status_code == 201
    assert response["reconciliation"]["suggested_count"] == 4
    assert response["reconciliation"]["unmatched_count"] == 1
    assert calls["kwargs"]["batch_id"] == 55
    assert calls["kwargs"]["company_id"] == 7


def test_get_workspace_returns_bank_and_system_buckets(monkeypatch):
    account = SimpleNamespace(id=21, company_id=1, to_dict=lambda: {"id": 21, "name": "Banco Principal"})
    batch = SimpleNamespace(id=77, to_dict=lambda: {"id": 77, "batch_code": "REC-077", "source_type": "ofx"})

    class _Row:
        def __init__(self, row_id, row_number, created_entry_id=None):
            self.id = row_id
            self.company_id = 1
            self.row_number = row_number
            self.created_entry_id = created_entry_id
            self.matched_entry_id = created_entry_id
            self.import_batch_id = 77
            self.processing_status = "validated"
            self.document_number = None
            self.description = f"Linha {row_number}"
            self.occurred_on = None
            self.due_date = None
            self.amount = 100
            self.movement_nature = "credit"
            self.bank_reference = f"REF-{row_number}"
            self.counterparty_name = "Cliente"
            self.raw_payload = {}
            self.normalized_payload = {"bank_account_id": 21}
            self.error_message = None

        def to_dict(self):
            return {
                "id": self.id,
                "company_id": self.company_id,
                "import_batch_id": self.import_batch_id,
                "row_number": self.row_number,
                "processing_status": self.processing_status,
                "document_number": self.document_number,
                "description": self.description,
                "occurred_on": self.occurred_on,
                "due_date": self.due_date,
                "amount": self.amount,
                "movement_nature": self.movement_nature,
                "bank_reference": self.bank_reference,
                "counterparty_name": self.counterparty_name,
                "raw_payload": self.raw_payload,
                "normalized_payload": self.normalized_payload,
                "error_message": self.error_message,
                "matched_entry_id": self.matched_entry_id,
                "created_entry_id": self.created_entry_id,
            }

    rows = [_Row(1, 1), _Row(2, 2, created_entry_id=501)]

    class _FakeAccountModel:
        id = _Column()
        company_id = _Column()
        deleted_at = _Column()
        query = _SingleResultQuery(account)

    class _FakeMatchQuery:
        def filter(self, *args, **kwargs):
            return self

        def order_by(self, *args, **kwargs):
            return self

        def all(self):
            return [
                SimpleNamespace(
                    id=801,
                    import_row_id=1,
                    financial_entry_id=401,
                    match_status="suggested",
                    confidence_score=0.91,
                    to_dict=lambda: {
                        "id": 801,
                        "import_row_id": 1,
                        "financial_entry_id": 401,
                        "match_status": "suggested",
                        "confidence_score": 0.91,
                    },
                )
            ]

    class _FakeMatchModel:
        company_id = _Column()
        import_batch_id = _Column()
        deleted_at = _Column()
        id = _Column()
        query = _FakeMatchQuery()

    monkeypatch.setattr(workspace_module.FinancialService, "_ensure_company_scope", lambda *args, **kwargs: None)
    monkeypatch.setattr(workspace_module, "FinancialBankAccount", _FakeAccountModel)
    monkeypatch.setattr(workspace_module, "FinancialReconciliationMatch", _FakeMatchModel)
    monkeypatch.setattr(workspace_module.FinancialReconciliationWorkspaceService, "_list_batches_for_bank_account", lambda *args, **kwargs: [batch])
    monkeypatch.setattr(workspace_module.FinancialReconciliationWorkspaceService, "_resolve_batch_rows", lambda *args, **kwargs: rows)
    monkeypatch.setattr(
        workspace_module.FinancialReconciliationWorkspaceService,
        "_serialize_row",
        lambda row, row_matches=None: {
            **row.to_dict(),
            "matches": workspace_module.FinancialReconciliationWorkspaceService._build_row_match_snapshot(row_matches or []),
            "needs_manual_action": not bool(row.created_entry_id) and not any(
                str(item.match_status or "").lower() == "confirmed" for item in (row_matches or [])
            ),
            "created_entry": None,
            "can_create_entry": not bool(row.created_entry_id),
            "is_fully_reconciled": bool(row.created_entry_id),
        },
    )
    monkeypatch.setattr(workspace_module.FinancialReconciliationWorkspaceService, "_load_workspace_entries", lambda **kwargs: [SimpleNamespace(id=901), SimpleNamespace(id=902)])
    monkeypatch.setattr(
        workspace_module.FinancialReconciliationWorkspaceService,
        "_serialize_system_entry",
        lambda entry, linked_row_ids=None: {
            "id": entry.id,
            "linked_rows_count": len(linked_row_ids or []),
            "is_reconciled": False,
        },
    )
    monkeypatch.setattr(workspace_module.FinancialReconciliationWorkspaceService, "_load_open_titles", lambda **kwargs: [])

    result, error = FinancialReconciliationWorkspaceService.get_workspace(
        company_id=1,
        bank_account_id=21,
        allowed_company_ids=[1],
    )

    assert error is None
    assert result["summary"]["pending_rows"] == 1
    assert result["summary"]["unmatched_bank_rows"] == 1
    assert result["summary"]["unmatched_system_rows"] == 2
    assert len(result["bank_rows"]) == 2
    assert len(result["bank_rows_without_link"]) == 1
    assert len(result["bank_rows_with_suggestion"]) == 1
    assert len(result["system_rows_without_link"]) == 2
    assert result["bank_rows"][0]["matches"]["suggested_count"] == 1


def test_cancel_reconciliations_batch_aggregates_success_and_failure(monkeypatch):
    monkeypatch.setattr(reconciliation_module.FinancialService, "_ensure_company_scope", lambda *args, **kwargs: None)

    def _fake_cancel_row_reconciliation(*, row_id, company_id, reason=None, allowed_company_ids=None):
        if row_id == 10:
            return {
                "row_id": 10,
                "reverted_matches": 1,
                "reverted_settlements": 2,
                "released_entry_ids": [501],
            }, None
        return None, "Linha sem conciliação ativa."

    monkeypatch.setattr(
        reconciliation_module.FinancialReconciliationService,
        "cancel_row_reconciliation",
        _fake_cancel_row_reconciliation,
    )

    result, error = FinancialReconciliationService.cancel_reconciliations_batch(
        row_ids=[10, 11],
        company_id=1,
        reason="Teste em lote",
        allowed_company_ids=[1],
    )

    assert error is None
    assert result["processed_rows"] == 2
    assert result["cancelled_rows"] == 1
    assert result["failed_rows"] == 1
    assert result["reverted_matches"] == 1
    assert result["reverted_settlements"] == 2
    assert result["released_entry_ids"] == [501]
    assert result["errors"][0]["row_id"] == 11
