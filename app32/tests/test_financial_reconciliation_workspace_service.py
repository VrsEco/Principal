import os
import sys
import io
from datetime import datetime
from types import SimpleNamespace

from flask import Flask

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import api.resources.financial as financial_resource_module
import services.financial_reconciliation_workspace_service as workspace_module
from services.financial_reconciliation_workspace_service import FinancialReconciliationWorkspaceService


class _Column:
    def __eq__(self, other):
        return ("eq", other)

    def is_(self, other):
        return ("is", other)


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
