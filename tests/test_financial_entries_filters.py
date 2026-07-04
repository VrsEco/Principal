from types import SimpleNamespace

from flask import Flask

from app32.api.resources.financial import FinancialEntryListResource
from app32.services.financial_service import FinancialService


class _FakeSettlementQuery:
    def __init__(self, settlements):
        self._settlements = list(settlements)

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def all(self):
        return list(self._settlements)


class _FakeLookupQuery:
    def __init__(self, items):
        self._items = list(items)

    def filter(self, *args, **kwargs):
        return self

    def all(self):
        return list(self._items)


class _FakeColumn:
    def in_(self, other):
        return ("in", other)

    def is_(self, other):
        return ("is", other)

    def __eq__(self, other):
        return ("eq", other)

    def __ne__(self, other):
        return ("ne", other)

    def asc(self):
        return "asc"

    def desc(self):
        return "desc"


def test_serialize_entry_list_exposes_latest_settlement_code(monkeypatch):
    from app32.services import financial_service as module

    entry = SimpleNamespace(
        id=10,
        company_id=3,
        to_dict=lambda: {
            "id": 10,
            "company_id": 3,
            "bank_account_id": None,
            "counterparty_id": None,
            "external_reference": "",
            "original_amount": 100.0,
            "movement_nature": "credit",
        },
    )
    settlement = SimpleNamespace(
        financial_entry_id=10,
        settlement_date=SimpleNamespace(isoformat=lambda: "2026-06-05"),
        settlement_code="BX-2026-0001",
        bank_account_id=None,
        principal_amount=100,
        gross_amount=100,
        net_amount=100,
        reconciliation_status="pending",
    )

    fake_settlement_model = SimpleNamespace(
        query=_FakeSettlementQuery([settlement]),
        company_id=_FakeColumn(),
        financial_entry_id=_FakeColumn(),
        deleted_at=_FakeColumn(),
        settlement_status=_FakeColumn(),
        settlement_date=_FakeColumn(),
        id=_FakeColumn(),
        bank_account_id=_FakeColumn(),
        principal_amount=_FakeColumn(),
    )
    fake_bank_account_model = SimpleNamespace(
        query=_FakeLookupQuery([]),
        company_id=_FakeColumn(),
        id=_FakeColumn(),
        deleted_at=_FakeColumn(),
    )
    fake_counterparty_model = SimpleNamespace(
        query=_FakeLookupQuery([]),
        company_id=_FakeColumn(),
        id=_FakeColumn(),
        deleted_at=_FakeColumn(),
    )

    monkeypatch.setattr(module, "FinancialSettlement", fake_settlement_model)
    monkeypatch.setattr(module, "FinancialBankAccount", fake_bank_account_model)
    monkeypatch.setattr(module, "FinancialCounterparty", fake_counterparty_model)

    items = FinancialService.serialize_entry_list([entry])

    assert items[0]["latest_settlement_code"] == "BX-2026-0001"
    assert items[0]["latest_settlement_date"] == "2026-06-05"


def test_financial_entry_list_resource_forwards_extended_filters(monkeypatch):
    captured = {}

    def _fake_list_entries(**kwargs):
        captured.update(kwargs)
        return ([{"id": 1}], None)

    monkeypatch.setattr("app32.api.resources.financial.get_request_company_id", lambda: 33)
    monkeypatch.setattr("app32.api.resources.financial.get_accessible_company_ids", lambda: [33])
    monkeypatch.setattr("app32.api.resources.financial.FinancialService.list_entries", _fake_list_entries)

    app = Flask(__name__)
    url = (
        "/api/financial/entries?"
        "company_id=33&status=settled&entry_type=receivable&movement_nature=credit"
        "&counterparty_id=44&counterparty_query=Acme&bank_query=Banco%20do%20Brasil"
        "&bank_account_id=55&bank_account_query=Conta%20Principal&document_number=NF-77"
        "&settlement_code=BX-12&description_query=mensalidade"
        "&general_query=Acme%20BX&amount_value=-1.234,56"
        "&competence_date_from=2026-06-01&competence_date_to=2026-06-30"
        "&due_date_from=2026-06-05&due_date_to=2026-06-25"
        "&settlement_date_from=2026-06-10&settlement_date_to=2026-06-20"
    )
    with app.test_request_context(url):
        result, status_code = FinancialEntryListResource.get.__wrapped__(FinancialEntryListResource())

    assert status_code == 200
    assert result == [{"id": 1}]
    assert captured["company_id"] == 33
    assert captured["allowed_company_ids"] == [33]
    assert captured["movement_nature"] == "credit"
    assert captured["counterparty_id"] == 44
    assert captured["counterparty_query"] == "Acme"
    assert captured["bank_query"] == "Banco do Brasil"
    assert captured["bank_account_id"] == 55
    assert captured["bank_account_query"] == "Conta Principal"
    assert captured["document_number"] == "NF-77"
    assert captured["settlement_code"] == "BX-12"
    assert captured["description_query"] == "mensalidade"
    assert captured["general_query"] == "Acme BX"
    assert str(captured["amount_value"]) == "1234.56"
    assert captured["competence_date_from"].isoformat() == "2026-06-01"
    assert captured["competence_date_to"].isoformat() == "2026-06-30"
    assert captured["due_date_from"].isoformat() == "2026-06-05"
    assert captured["due_date_to"].isoformat() == "2026-06-25"
    assert captured["settlement_date_from"].isoformat() == "2026-06-10"
    assert captured["settlement_date_to"].isoformat() == "2026-06-20"
