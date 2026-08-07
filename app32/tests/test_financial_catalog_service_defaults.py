import os
import sys
from decimal import Decimal

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import services.financial_catalog_service as catalog_module
from models.financial import FinancialCounterparty
from services.financial_catalog_service import FinancialCatalogService


class _Column:
    def __eq__(self, other):
        return ("eq", other)

    def is_(self, other):
        return ("is", other)


class _QueryStub:
    def __init__(self, result=None):
        self.result = result

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self.result


def test_create_cost_center_preserves_default_suggestion(monkeypatch):
    captured = {}

    class _FakeCostCenter:
        company_id = _Column()
        code = _Column()
        deleted_at = _Column()
        query = _QueryStub(None)

        def __init__(self, **kwargs):
            self.id = 77
            self.__dict__.update(kwargs)

        def to_dict(self):
            return dict(self.__dict__)

    monkeypatch.setattr(catalog_module, "FinancialCostCenter", _FakeCostCenter)
    monkeypatch.setitem(FinancialCatalogService.CATALOGS, "cost_centers", {
        "model": _FakeCostCenter,
        "create_schema": catalog_module.FinancialCostCenterInput,
        "update_schema": catalog_module.FinancialCostCenterUpdateInput,
        "code_field": "code",
        "company_fk_fields": ["parent_id"],
    })
    monkeypatch.setattr(catalog_module.FinancialCatalogService, "_validate_scope", lambda **kwargs: None)
    monkeypatch.setattr(catalog_module.FinancialCatalogService, "_validate_related_scope", lambda **kwargs: None)
    monkeypatch.setattr(catalog_module.FinancialCatalogService, "_clear_default_cost_center_suggestions", lambda **kwargs: captured.setdefault("clear_kwargs", kwargs))
    monkeypatch.setattr(catalog_module.db.session, "add", lambda obj: captured.setdefault("added", obj))
    monkeypatch.setattr(catalog_module.db.session, "flush", lambda: captured.setdefault("flushed", True))
    monkeypatch.setattr(catalog_module.db.session, "commit", lambda: captured.setdefault("committed", True))
    monkeypatch.setattr(catalog_module.db.session, "rollback", lambda: captured.setdefault("rollback", True))

    result, error = FinancialCatalogService.create_item(
        catalog_type="cost_centers",
        payload={
            "company_id": 9,
            "code": "CC-001",
            "name": "Centro padrão",
            "is_default_suggestion": True,
        },
        allowed_company_ids=[9],
    )

    assert error is None
    assert result is not None
    assert result["is_default_suggestion"] is True
    assert captured["clear_kwargs"]["exclude_item_id"] == 77


def test_prepare_cost_center_payload_maps_account_level_type():
    payload = FinancialCatalogService._prepare_catalog_payload(
        catalog_type="cost_centers",
        company_id=9,
        data={
            "company_id": 9,
            "code": "1.01",
            "name": "Administrativo",
            "account_level_type": "synthetic",
            "metadata_json": {"external_code": "ERP-01"},
        },
    )

    assert payload["accepts_posting"] is False
    assert payload["metadata_json"]["account_level_type"] == "synthetic"
    assert payload["metadata_json"]["external_code"] == "ERP-01"


def test_prepare_bank_account_payload_maps_overdraft_limit_to_metadata():
    payload = FinancialCatalogService._prepare_catalog_payload(
        catalog_type="bank_accounts",
        company_id=9,
        data={
            "company_id": 9,
            "code": "001",
            "name": "Conta Movimento",
            "metadata_json": {"notes": "Conta principal"},
            "overdraft_limit": Decimal("12500.75"),
        },
    )

    assert "overdraft_limit" not in payload
    assert payload["metadata_json"]["notes"] == "Conta principal"
    assert payload["metadata_json"]["overdraft_limit"] == 12500.75


def test_validate_related_scope_rejects_analytic_cost_center_parent(monkeypatch):
    class _AnalyticParent:
        id = 55
        accepts_posting = True

    class _FakeCostCenter:
        id = _Column()
        company_id = _Column()
        deleted_at = _Column()
        query = _QueryStub(_AnalyticParent())

    monkeypatch.setattr(catalog_module, "FinancialCostCenter", _FakeCostCenter)

    error = FinancialCatalogService._validate_related_scope(
        catalog_type="cost_centers",
        company_id=9,
        data={"parent_id": 55},
    )

    assert error == "Centro analítico não pode ser usado como centro pai."


def test_validate_cost_center_default_rule_requires_analytic():
    error = FinancialCatalogService._validate_cost_center_default_rule(
        {
            "is_default_suggestion": True,
            "accepts_posting": False,
        }
    )

    assert error == "Somente centros de custo analíticos podem ser definidos como padrão."


def test_prepare_counterparty_payload_maps_roles_to_metadata():
    payload = FinancialCatalogService._prepare_catalog_payload(
        catalog_type="counterparties",
        company_id=9,
        data={
            "company_id": 9,
            "code": "001",
            "name": "Cliente Teste",
            "is_customer": True,
            "is_supplier": False,
            "metadata_json": {"origin": "manual"},
        },
    )

    assert "is_customer" not in payload
    assert "is_supplier" not in payload
    assert payload["metadata_json"]["is_customer"] is True
    assert payload["metadata_json"]["is_supplier"] is False
    assert payload["metadata_json"]["origin"] == "manual"


def test_prepare_counterparty_payload_maps_customer_zip_code_to_fiscal_aliases():
    payload = FinancialCatalogService._prepare_catalog_payload(
        catalog_type="counterparties",
        company_id=9,
        data={
            "company_id": 9,
            "code": "001",
            "name": "Cliente Teste",
            "zip_code": "41.820-021",
            "is_customer": True,
            "metadata_json": {"origin": "manual"},
        },
    )

    assert "zip_code" not in payload
    assert payload["metadata_json"]["zip_code"] == "41820021"
    assert payload["metadata_json"]["Endereco_Cep"] == "41820021"
    assert payload["metadata_json"]["endereco_cep"] == "41820021"
    assert payload["metadata_json"]["cep"] == "41820021"
    assert payload["metadata_json"]["origin"] == "manual"


def test_prepare_counterparty_payload_maps_full_address_to_fiscal_aliases():
    payload = FinancialCatalogService._prepare_catalog_payload(
        catalog_type="counterparties",
        company_id=9,
        data={
            "company_id": 9,
            "name": "Cliente Teste",
            "address_line": "Rua das Flores",
            "address_number": "120",
            "complement": "Sala 4",
            "district": "Centro",
            "city_name": "Salvador",
            "city_code_ibge": "2927408",
            "uf": "ba",
            "country_code": "bra",
            "metadata_json": {"origin": "manual"},
        },
    )

    metadata = payload["metadata_json"]
    assert metadata["address_line"] == "Rua das Flores"
    assert metadata["Endereco_Logradouro"] == "Rua das Flores"
    assert metadata["Endereco_Numero"] == "120"
    assert metadata["Endereco_Complemento"] == "Sala 4"
    assert metadata["Endereco_Bairro"] == "Centro"
    assert metadata["Endereco_Cidade_Nome"] == "Salvador"
    assert metadata["Endereco_Cidade_Codigo"] == "2927408"
    assert metadata["Endereco_Estado"] == "BA"
    assert metadata["Endereco_Pais"] == "BRA"


def test_financial_counterparty_to_dict_exposes_zip_code_from_metadata():
    counterparty = FinancialCounterparty(
        company_id=9,
        code="001",
        name="Cliente Teste",
        metadata_json={"Endereco_Cep": "41820021", "is_customer": True},
    )

    payload = counterparty.to_dict()

    assert payload["zip_code"] == "41820021"
    assert payload["metadata_json"]["Endereco_Cep"] == "41820021"


def test_financial_counterparty_to_dict_exposes_full_address_from_metadata():
    counterparty = FinancialCounterparty(
        company_id=9,
        code="001",
        name="Cliente Teste",
        metadata_json={
            "Endereco_Logradouro": "Rua das Flores",
            "Endereco_Numero": "120",
            "Endereco_Complemento": "Sala 4",
            "Endereco_Bairro": "Centro",
            "Endereco_Cidade_Nome": "Salvador",
            "Endereco_Cidade_Codigo": "2927408",
            "Endereco_Estado": "BA",
            "Endereco_Pais": "BRA",
        },
    )

    payload = counterparty.to_dict()

    assert payload["address_line"] == "Rua das Flores"
    assert payload["address_number"] == "120"
    assert payload["complement"] == "Sala 4"
    assert payload["district"] == "Centro"
    assert payload["city_name"] == "Salvador"
    assert payload["city_code_ibge"] == "2927408"
    assert payload["uf"] == "BA"
    assert payload["country_code"] == "BRA"


def test_validate_related_scope_requires_counterparty_role_flag():
    error = FinancialCatalogService._validate_related_scope(
        catalog_type="counterparties",
        company_id=9,
        data={"metadata_json": {"is_customer": False, "is_supplier": False}},
    )

    assert error == "Selecione ao menos uma classificação para o favorecido: Cliente, Fornecedor ou ambos."
