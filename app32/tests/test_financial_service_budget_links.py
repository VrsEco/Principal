import os
import sys
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import services.financial_service as financial_module
from services.financial_service import FinancialService


class _Column:
    def __eq__(self, other):
        return ("eq", other)


class _Predicate:
    def is_(self, other):
        return self


class _QueryStub:
    def __init__(self, result):
        self._result = result

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self._result


def test_create_entry_applies_budget_links_and_syncs_metadata(monkeypatch):
    captured = {}

    class _FakeEntry:
        company_id = _Column()
        entry_code = _Column()
        query = _QueryStub(None)

        def __init__(self, **kwargs):
            captured["kwargs"] = kwargs
            self.__dict__.update(kwargs)

    monkeypatch.setattr(financial_module, "FinancialEntry", _FakeEntry)
    monkeypatch.setattr(financial_module.FinancialService, "_ensure_company_scope", lambda *args, **kwargs: None)
    monkeypatch.setattr(financial_module.FinancialService, "_validate_operational_links", lambda **kwargs: None)
    monkeypatch.setattr(
        financial_module.FinancialService,
        "_resolve_budget_links",
        lambda **kwargs: (
            {
                "budget_line_id": 101,
                "budget_contract_id": 202,
                "budget_document_id": 303,
            },
            None,
        ),
    )
    monkeypatch.setattr(financial_module.FinancialCatalogService, "validate_reference_ids", lambda **kwargs: None)
    monkeypatch.setattr(financial_module.db.session, "add", lambda obj: captured.setdefault("added", obj))
    monkeypatch.setattr(financial_module.db.session, "commit", lambda: captured.setdefault("committed", True))
    monkeypatch.setattr(financial_module.db.session, "rollback", lambda: captured.setdefault("rollback", True))

    entry, error = FinancialService.create_entry(
        payload={
            "company_id": 9,
            "entry_code": "ENT-001",
            "entry_type": "payable",
            "movement_nature": "debit",
            "origin_type": "manual",
            "status": "draft",
            "review_status": "pending_review",
            "description": "Lançamento teste",
            "competence_date": date(2026, 3, 27),
            "due_date": date(2026, 3, 27),
            "original_amount": Decimal("150.00"),
            "currency_code": "BRL",
            "metadata_json": {"source": "test"},
        },
        allowed_company_ids=[9],
    )

    assert error is None
    assert entry is not None
    assert captured["committed"] is True
    assert captured["kwargs"]["budget_line_id"] == 101
    assert captured["kwargs"]["budget_contract_id"] == 202
    assert captured["kwargs"]["budget_document_id"] == 303
    assert captured["kwargs"]["metadata_json"]["source"] == "test"
    assert captured["kwargs"]["metadata_json"]["budget_line_id"] == 101
    assert captured["kwargs"]["metadata_json"]["budget_contract_id"] == 202
    assert captured["kwargs"]["metadata_json"]["budget_document_id"] == 303


def test_update_entry_accepts_same_entry_code_in_payload(monkeypatch):
    class _Query:
        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return entry

    class _FakeEntry:
        id = _Column()
        company_id = _Column()
        deleted_at = _Predicate()
        query = _Query()

    entry = SimpleNamespace(
        id=1,
        company_id=9,
        entry_code="ENT-001",
        activity_id=None,
        process_instance_id=None,
        routine_id=None,
        bank_account_id=None,
        chart_account_id=None,
        cost_center_id=None,
        counterparty_id=None,
        budget_line_id=None,
        budget_contract_id=None,
        budget_document_id=None,
        metadata_json={},
    )

    monkeypatch.setattr(financial_module, "FinancialEntry", _FakeEntry)
    monkeypatch.setattr(financial_module.FinancialService, "_ensure_company_scope", lambda *args, **kwargs: None)
    monkeypatch.setattr(financial_module.FinancialService, "_validate_operational_links", lambda **kwargs: None)
    monkeypatch.setattr(financial_module.FinancialService, "_resolve_budget_links", lambda **kwargs: ({}, None))
    monkeypatch.setattr(financial_module.FinancialCatalogService, "validate_reference_ids", lambda **kwargs: None)
    monkeypatch.setattr(financial_module, "is_administrator", lambda company_id: True)
    monkeypatch.setattr(financial_module.FinancialService, "is_entry_reconciled", lambda current: False)
    monkeypatch.setattr(
        "services.financial_bordero_service.FinancialBorderoService.get_active_bordero_for_entry",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(financial_module.db.session, "commit", lambda: None)
    monkeypatch.setattr(financial_module.db.session, "rollback", lambda: None)

    result, error = FinancialService.update_entry(
        entry_id=1,
        company_id=9,
        payload={
            "entry_code": "ENT-001",
            "description": "Lançamento atualizado",
        },
        allowed_company_ids=[9],
    )

    assert error is None
    assert result is not None
    assert entry.entry_code == "ENT-001"
    assert entry.description == "Lançamento atualizado"


def test_update_entry_rejects_entry_code_change(monkeypatch):
    class _Query:
        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return entry

    class _FakeEntry:
        id = _Column()
        company_id = _Column()
        deleted_at = _Predicate()
        query = _Query()

    entry = SimpleNamespace(
        id=1,
        company_id=9,
        entry_code="ENT-001",
        activity_id=None,
        process_instance_id=None,
        routine_id=None,
        bank_account_id=None,
        chart_account_id=None,
        cost_center_id=None,
        counterparty_id=None,
        budget_line_id=None,
        budget_contract_id=None,
        budget_document_id=None,
        metadata_json={},
    )

    monkeypatch.setattr(financial_module, "FinancialEntry", _FakeEntry)
    monkeypatch.setattr(financial_module.FinancialService, "_ensure_company_scope", lambda *args, **kwargs: None)
    monkeypatch.setattr(financial_module, "is_administrator", lambda company_id: True)
    monkeypatch.setattr(financial_module.FinancialService, "is_entry_reconciled", lambda current: False)
    monkeypatch.setattr(
        "services.financial_bordero_service.FinancialBorderoService.get_active_bordero_for_entry",
        lambda **kwargs: None,
    )

    result, error = FinancialService.update_entry(
        entry_id=1,
        company_id=9,
        payload={"entry_code": "ENT-999"},
        allowed_company_ids=[9],
    )

    assert result is None
    assert error == "O código do lançamento não pode ser alterado após a criação."
