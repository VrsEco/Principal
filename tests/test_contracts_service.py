from pathlib import Path
import sys
from decimal import Decimal
from datetime import date
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app32"))

from services.contracts_service import ContractService
from services.contracts_catalog_service import ContractsCatalogService


def test_calculate_total_price_handles_brazilian_number_formats():
    total = ContractService.calculate_total_price("2,5", "1.200,40")
    assert total == Decimal("3001.00")


def test_normalize_bool_accepts_expected_truthy_values():
    assert ContractService._normalize_bool("sim") is True
    assert ContractService._normalize_bool("on") is True
    assert ContractService._normalize_bool("0") is False


def test_normalize_int_returns_none_for_invalid_values():
    assert ContractService._normalize_int("") is None
    assert ContractService._normalize_int("abc") is None
    assert ContractService._normalize_int("12") == 12


def test_normalize_date_parses_iso_pattern():
    value = ContractService._normalize_date("2026-05-01")
    assert value.isoformat() == "2026-05-01"


def test_update_party_requires_explicit_customer_or_supplier():
    party = SimpleNamespace(
        name="Favorecido",
        legal_name=None,
        document_type=None,
        document_number=None,
        email=None,
        phone=None,
        is_customer=False,
        is_supplier=False,
        status="active",
        notes=None,
        financial_counterparty_id=None,
        updated_by_user_id=None,
    )
    with pytest.raises(ValueError):
        ContractService.update_party(party=party, payload={"name": "Fav", "is_customer": "", "is_supplier": ""}, user_id=1, is_new=True)


def test_update_contract_general_keeps_existing_fields_when_payload_is_partial():
    contract = SimpleNamespace(
        title="Contrato A",
        party_id=7,
        status="draft",
        contract_type="prestacao",
        currency_code="BRL",
        signed_at=date(2026, 5, 1),
        service_start_at=None,
        service_end_at=None,
        billing_start_at=None,
        billing_end_at=None,
        last_billing_at=None,
        periodicity="monthly",
        competence_rule="mes atual",
        due_rule="30 dias",
        renewal_rule="auto",
        notes="base",
        updated_by_user_id=None,
    )
    ContractService.update_contract_general(contract=contract, payload={"title": "Contrato B"}, user_id=9, is_new=True)
    assert contract.title == "Contrato B"
    assert contract.periodicity == "monthly"
    assert contract.signed_at.isoformat() == "2026-05-01"


def test_update_contract_general_supports_last_billing_and_binary_status():
    contract = SimpleNamespace(
        title="Contrato X",
        party_id=9,
        status="signed",
        contract_type=None,
        currency_code="BRL",
        signed_at=None,
        service_start_at=None,
        service_end_at=None,
        billing_start_at=None,
        billing_end_at=None,
        last_billing_at=None,
        periodicity=None,
        competence_rule=None,
        due_rule=None,
        renewal_rule=None,
        notes=None,
        updated_by_user_id=None,
    )
    ContractService.update_contract_general(
        contract=contract,
        payload={"status": "inactive", "last_billing_at": "2026-04-30"},
        user_id=3,
        is_new=True,
    )
    assert contract.status == "inactive"
    assert contract.last_billing_at.isoformat() == "2026-04-30"


def test_get_contract_status_group_maps_legacy_active_statuses():
    contract = SimpleNamespace(status="signed")
    assert ContractService.get_contract_status_group(contract) == "active"


def test_infer_document_type_detects_cpf_and_cnpj():
    assert ContractService.infer_document_type("123.456.789-01") == "cpf"
    assert ContractService.infer_document_type("12.345.678/0001-99") == "cnpj"
    assert ContractService.infer_document_type("ABC") is None


def test_resolve_company_code_uses_first_two_chars_of_client_code(monkeypatch):
    monkeypatch.setattr(
        ContractService,
        "get_company",
        staticmethod(lambda company_id: SimpleNamespace(id=company_id, client_code="vt001", name="Versus Tech")),
    )
    assert ContractService._resolve_company_code(9) == "VT"


def test_next_structured_code_scopes_sequence_by_marker(monkeypatch):
    monkeypatch.setattr(
        ContractService,
        "get_company",
        staticmethod(lambda company_id: SimpleNamespace(id=company_id, client_code="AA", name="Alpha")),
    )

    class _Query:
        def with_entities(self, *_args, **_kwargs):
            return self

        def filter(self, *_args, **_kwargs):
            return self

        def all(self):
            return [("AA.F.001",), ("AA.F.009",), ("AA.N.002",), ("BB.F.111",), (None,)]

    class _Model:
        query = _Query()
        code = object()
        company_id = object()

    assert ContractService._next_structured_code(_Model, 9, "F") == "AA.F.010"
    assert ContractService._next_structured_code(_Model, 9, "N") == "AA.N.003"


def test_contracts_catalog_compose_code_supports_root_and_child():
    assert ContractsCatalogService._compose_code(None, "001") == "001"
    assert ContractsCatalogService._compose_code("001", "010") == "001.010"


def test_add_contract_item_uses_catalog_defaults(monkeypatch):
    catalog_item = SimpleNamespace(
        id=55,
        company_id=9,
        code="001.010",
        name="Consultoria Estratégica",
        item_kind="service",
        unit_code="H",
        accepts_contracting=True,
    )

    class _Query:
        def filter(self, *_args, **_kwargs):
            return self

        def first(self):
            return catalog_item

    class _CatalogModel:
        query = _Query()
        id = object()
        company_id = object()
        deleted_at = SimpleNamespace(is_=lambda *_args, **_kwargs: None)
        accepts_contracting = SimpleNamespace(is_=lambda *_args, **_kwargs: None)

    monkeypatch.setattr("services.contracts_service.ContractCatalogItem", _CatalogModel)
    monkeypatch.setattr("services.contracts_service.db.session.add", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("services.contracts_service.db.session.commit", lambda *_args, **_kwargs: None)

    contract = SimpleNamespace(company_id=9, id=77)
    item = ContractService.add_contract_item(
        contract=contract,
        payload={"contract_catalog_item_id": "55", "quantity": "2", "unit_price": "10,00"},
    )

    assert item.contract_catalog_item_id == 55
    assert item.item_code == "001.010"
    assert item.item_type == "service"
    assert item.description == "Consultoria Estratégica"
    assert item.unit_code == "H"
