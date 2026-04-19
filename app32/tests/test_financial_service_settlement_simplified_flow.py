import io
import os
import sys
from datetime import date
from decimal import Decimal

from flask import Flask
from werkzeug.datastructures import FileStorage

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import services.financial_service as financial_module
import services.financial_bordero_service as bordero_module
from services.financial_service import FinancialService


class _Column:
    def __eq__(self, other):
        return ("eq", other)

    def is_(self, other):
        return ("is", other)

    def like(self, other):
        return ("like", other)

    def in_(self, other):
        return ("in", other)

    def desc(self):
        return self


class _QueryStub:
    def __init__(self, result):
        self._result = result

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def first(self):
        return self._result


class _SequenceQueryStub(_QueryStub):
    def __init__(self, results):
        self._results = list(results)

    def first(self):
        if self._results:
            return self._results.pop(0)
        return None


def test_create_settlement_generates_code_when_not_informed(monkeypatch):
    captured = {}

    class _FakeEntry:
        id = _Column()
        company_id = _Column()
        deleted_at = _Column()

        def __init__(self):
            self.original_amount = Decimal("500.00")
            self.status = "posted"

    class _FakeSettlement:
        company_id = _Column()
        settlement_code = _Column()
        deleted_at = _Column()
        id = _Column()
        principal_amount = _Column()
        financial_entry_id = _Column()
        settlement_status = _Column()
        query = _SequenceQueryStub([type("PreviousSettlement", (), {"settlement_code": "LIQ-000014", "id": 14})(), None])

        def __init__(self, **kwargs):
            captured["kwargs"] = kwargs
            self.__dict__.update(kwargs)

    entry = _FakeEntry()
    entry_query = _QueryStub(entry)

    monkeypatch.setattr(financial_module, "FinancialEntry", type("FinancialEntryStub", (), {
        "id": _Column(),
        "company_id": _Column(),
        "deleted_at": _Column(),
        "query": entry_query,
    }))
    monkeypatch.setattr(financial_module, "FinancialSettlement", _FakeSettlement)
    monkeypatch.setattr(financial_module.FinancialService, "_ensure_company_scope", lambda *args, **kwargs: None)
    monkeypatch.setattr(financial_module.FinancialCatalogService, "validate_reference_ids", lambda **kwargs: None)
    monkeypatch.setattr(
        financial_module.db.session,
        "query",
        lambda *args, **kwargs: type("AggQuery", (), {"filter": lambda self, *a, **k: self, "scalar": lambda self: Decimal("0")})(),
    )
    monkeypatch.setattr(financial_module.db.session, "add", lambda obj: captured.setdefault("added", obj))
    monkeypatch.setattr(financial_module.db.session, "commit", lambda: captured.setdefault("committed", True))
    monkeypatch.setattr(financial_module.db.session, "rollback", lambda: captured.setdefault("rollback", True))
    monkeypatch.setattr(bordero_module.FinancialBorderoService, "get_active_bordero_for_entry", lambda **kwargs: None)

    settlement, error = FinancialService.create_settlement(
        payload={
            "company_id": 7,
            "financial_entry_id": 99,
            "settlement_type": "manual",
            "settlement_date": date(2026, 3, 29),
            "bank_account_id": 3,
            "principal_amount": Decimal("120.00"),
            "notes": "Baixa simplificada",
            "metadata_json": {
                "history": "Baixa simplificada",
                "payment_method_id": 8,
                "payment_method_label": "PIX",
            },
        },
        allowed_company_ids=[7],
    )

    assert error is None
    assert settlement is not None
    assert captured["kwargs"]["settlement_code"] == "LIQ-000015"
    assert captured["kwargs"]["metadata_json"]["history"] == "Baixa simplificada"
    assert captured["committed"] is True
    assert entry.status == "partially_settled"


def test_create_settlement_adds_financial_title_snapshot(monkeypatch):
    captured = {}

    class _FakeEntry:
        id = _Column()
        company_id = _Column()
        deleted_at = _Column()

        def __init__(self):
            self.id = 99
            self.company_id = 7
            self.original_amount = Decimal("475.00")
            self.status = "posted"
            self.financial_schedule_id = 77

    class _FakeSchedule:
        id = _Column()
        company_id = _Column()
        deleted_at = _Column()
        query = _QueryStub(type("Schedule", (), {
            "id": 77,
            "company_id": 7,
            "schedule_code": "TIT-077",
            "template_amount": Decimal("500.00"),
            "metadata_json": {"discount_amount_override": "25"},
            "competence_date": date(2026, 3, 5),
            "start_date": date(2026, 3, 5),
            "first_due_date": date(2026, 3, 22),
            "next_due_date": date(2026, 3, 22),
        })())

    class _FakeSettlement:
        company_id = _Column()
        settlement_code = _Column()
        deleted_at = _Column()
        id = _Column()
        principal_amount = _Column()
        financial_entry_id = _Column()
        settlement_status = _Column()
        query = _SequenceQueryStub([type("PreviousSettlement", (), {"settlement_code": "LIQ-000020", "id": 20})(), None])

        def __init__(self, **kwargs):
            captured["kwargs"] = kwargs
            self.__dict__.update(kwargs)

    entry = _FakeEntry()
    monkeypatch.setattr(financial_module, "FinancialEntry", type("FinancialEntryStub", (), {
        "id": _Column(),
        "company_id": _Column(),
        "deleted_at": _Column(),
        "query": _QueryStub(entry),
    }))
    monkeypatch.setattr(financial_module, "FinancialSchedule", _FakeSchedule)
    monkeypatch.setattr(financial_module, "FinancialSettlement", _FakeSettlement)
    monkeypatch.setattr(financial_module.FinancialService, "_ensure_company_scope", lambda *args, **kwargs: None)
    monkeypatch.setattr(financial_module.FinancialCatalogService, "validate_reference_ids", lambda **kwargs: None)
    monkeypatch.setattr(
        financial_module.db.session,
        "query",
        lambda *args, **kwargs: type("AggQuery", (), {"filter": lambda self, *a, **k: self, "scalar": lambda self: Decimal("100")})(),
    )
    monkeypatch.setattr(financial_module.db.session, "add", lambda obj: captured.setdefault("added", obj))
    monkeypatch.setattr(financial_module.db.session, "commit", lambda: captured.setdefault("committed", True))
    monkeypatch.setattr(financial_module.db.session, "rollback", lambda: captured.setdefault("rollback", True))
    monkeypatch.setattr(bordero_module.FinancialBorderoService, "get_active_bordero_for_entry", lambda **kwargs: None)

    settlement, error = FinancialService.create_settlement(
        payload={
            "company_id": 7,
            "financial_entry_id": 99,
            "settlement_type": "manual",
            "settlement_date": date(2026, 3, 29),
            "principal_amount": Decimal("120.00"),
        },
        allowed_company_ids=[7],
    )

    assert error is None
    assert settlement is not None
    snapshot = captured["kwargs"]["metadata_json"]["financial_title_snapshot"]
    assert snapshot["financial_schedule_id"] == 77
    assert snapshot["updated_amount"] == 475.0
    assert snapshot["settled_principal_before"] == 100.0
    assert snapshot["settled_principal_current"] == 120.0
    assert snapshot["settled_principal_after"] == 220.0
    assert snapshot["open_principal_after"] == 255.0


def test_upload_and_delete_settlement_attachment_updates_metadata(tmp_path, monkeypatch):
    class _FakeSettlement:
        id = _Column()
        company_id = _Column()
        deleted_at = _Column()

        def __init__(self):
            self.id = 33
            self.company_id = 5
            self.metadata_json = {}

    settlement = _FakeSettlement()
    settlement_query = _QueryStub(settlement)

    monkeypatch.setattr(financial_module, "FinancialSettlement", type("SettlementStub", (), {
        "id": _Column(),
        "company_id": _Column(),
        "deleted_at": _Column(),
        "query": settlement_query,
    }))
    monkeypatch.setattr(financial_module.FinancialService, "_ensure_company_scope", lambda *args, **kwargs: None)
    monkeypatch.setattr(financial_module.db.session, "commit", lambda: None)

    app = Flask(__name__)
    app.config["UPLOAD_FOLDER"] = str(tmp_path)

    with app.app_context():
        attachment, error = FinancialService.upload_settlement_attachment(
            settlement_id=33,
            company_id=5,
            file=FileStorage(stream=io.BytesIO(b"arquivo"), filename="comprovante.pdf", content_type="application/pdf"),
            allowed_company_ids=[5],
        )

        assert error is None
        assert attachment is not None
        assert len(settlement.metadata_json["attachments"]) == 1
        saved_file = settlement.metadata_json["attachments"][0]["stored_name"]
        saved_path = tmp_path / "financial_settlements" / "5" / "33" / saved_file
        assert saved_path.exists()

        removed, delete_error = FinancialService.delete_settlement_attachment(
            settlement_id=33,
            company_id=5,
            attachment_id=attachment["id"],
            allowed_company_ids=[5],
        )

        assert delete_error is None
        assert removed["id"] == attachment["id"]
        assert settlement.metadata_json["attachments"] == []
        assert not saved_path.exists()


def test_create_settlement_rejects_zero_principal_amount(monkeypatch):
    class _FakeEntry:
        id = _Column()
        company_id = _Column()
        deleted_at = _Column()

        def __init__(self):
            self.original_amount = Decimal("500.00")
            self.status = "posted"

    class _FakeSettlement:
        company_id = _Column()
        settlement_code = _Column()
        deleted_at = _Column()
        id = _Column()
        principal_amount = _Column()
        financial_entry_id = _Column()
        settlement_status = _Column()
        query = _SequenceQueryStub([None])

    entry = _FakeEntry()
    entry_query = _QueryStub(entry)

    monkeypatch.setattr(financial_module, "FinancialEntry", type("FinancialEntryStub", (), {
        "id": _Column(),
        "company_id": _Column(),
        "deleted_at": _Column(),
        "query": entry_query,
    }))
    monkeypatch.setattr(financial_module, "FinancialSettlement", _FakeSettlement)
    monkeypatch.setattr(financial_module.FinancialService, "_ensure_company_scope", lambda *args, **kwargs: None)
    monkeypatch.setattr(financial_module.FinancialCatalogService, "validate_reference_ids", lambda **kwargs: None)
    monkeypatch.setattr(
        financial_module.db.session,
        "query",
        lambda *args, **kwargs: type("AggQuery", (), {"filter": lambda self, *a, **k: self, "scalar": lambda self: Decimal("0")})(),
    )
    monkeypatch.setattr(financial_module.db.session, "add", lambda obj: (_ for _ in ()).throw(AssertionError("não deveria persistir")))
    monkeypatch.setattr(financial_module.db.session, "commit", lambda: (_ for _ in ()).throw(AssertionError("não deveria commitar")))
    monkeypatch.setattr(bordero_module.FinancialBorderoService, "get_active_bordero_for_entry", lambda **kwargs: None)

    settlement, error = FinancialService.create_settlement(
        payload={
            "company_id": 7,
            "financial_entry_id": 99,
            "settlement_type": "manual",
            "settlement_date": date(2026, 3, 29),
            "bank_account_id": 3,
            "principal_amount": Decimal("0"),
            "notes": "Baixa zerada inválida",
            "metadata_json": {
                "history": "Baixa zerada inválida",
            },
        },
        allowed_company_ids=[7],
    )

    assert settlement is None
    assert error == "Baixa inválida: o valor principal deve ser maior que zero."
    assert entry.status == "posted"
