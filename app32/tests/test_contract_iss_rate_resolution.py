from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from services.contracts_service import ContractService


def test_effective_iss_rate_prefers_issuer_rule_over_item_fallback():
    legal_entity = SimpleNamespace(
        metadata_json={
            "iss_rate_rules": [
                {"effective_from": "2026-06-01", "effective_to": None, "percent": "2.73"}
            ]
        }
    )
    contract = SimpleNamespace(contracting_legal_entity=legal_entity)

    rate, source, rule = ContractService._resolve_effective_iss_rate_percent(
        contract=contract,
        catalog_item=None,
        reference_date=date(2026, 6, 5),
        fallback_rate="2.5",
    )

    assert rate == Decimal("2.7300")
    assert source == "issuer"
    assert rule["percent"] == "2.73"


def test_nfse_export_prefers_fiscal_issuer_iss_rate_over_retention_snapshot(monkeypatch):
    native_billing = SimpleNamespace(
        party=None,
        gross_amount=Decimal("1000.00"),
        metadata_json={"fiscal_snapshot": {"issuer_iss_rate": "2.73"}},
    )

    monkeypatch.setattr(
        ContractService,
        "_get_fiscal_invoice_state",
        staticmethod(lambda _billing: {"fiscal_data": {"issuer_iss_rate": "2.73"}}),
    )
    monkeypatch.setattr(ContractService, "_party_metadata_sources", staticmethod(lambda *_args, **_kwargs: []))
    monkeypatch.setattr(ContractService, "_billing_item_metadata_sources", staticmethod(lambda *_args, **_kwargs: []))
    monkeypatch.setattr(
        ContractService,
        "_metadata_sources",
        staticmethod(lambda *_args, **_kwargs: [{"issuer_iss_rate": "2.73"}]),
    )
    monkeypatch.setattr(
        ContractService,
        "_retention_totals_by_kind",
        staticmethod(lambda _billing: ({"iss": Decimal("25.00")}, {"iss": Decimal("2.5")})),
    )
    monkeypatch.setattr(ContractService, "_collect_retention_observation_lines", staticmethod(lambda **_kwargs: []))
    monkeypatch.setattr(ContractService, "_billing_item_descriptions", staticmethod(lambda _billing: "Serviço"))

    row = ContractService._build_fiscal_invoice_nfse_row(company_id=1, native_billing=native_billing)

    assert row["Aliquota_ISS"] == "2.73"
    assert row["Valor_ISS"] == "25,00"
