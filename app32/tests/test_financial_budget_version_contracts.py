import os
import sys
from datetime import date

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import models
from models import financial_budget as financial_budget_models

if not hasattr(models, "FinancialBudgetCycle"):
    models.FinancialBudgetCycle = financial_budget_models.FinancialBudgetCycle

import services.financial_budget_service as budget_service_module
from services.financial_budget_service import FinancialBudgetService
from services.financial_budget_code_service import FinancialBudgetCodeService
from models.financial_budget import FinancialBudgetContract, FinancialBudgetDocument, FinancialBudgetLine, FinancialBudgetVersion


class _Column:
    def __eq__(self, other):
        return ("eq", other)

    def is_(self, other):
        return ("is", other)


class _QueryStub:
    def __init__(self, result=None):
        self.result = result
        self.filters = []

    def filter(self, *args, **kwargs):
        self.filters.append((args, kwargs))
        return self

    def first(self):
        return self.result

    def all(self):
        return [] if self.result is None else self.result


def test_budget_version_line_contract_document_to_dict_preserve_hierarchical_codes():
    version = FinancialBudgetVersion(
        company_id=9,
        code="AA.O.2026.CAPEX.1",
        name="CAPEX 2026",
        scenario_type="original",
        status="draft",
        period_start=date(2026, 1, 1),
        period_end=date(2026, 12, 31),
        notes="Plano CAPEX",
        metadata_json={"budget_cycle_code": "AA.BC.2026", "budget_category": "CAPEX"},
    )
    line = FinancialBudgetLine(
        company_id=9,
        budget_version_id=1,
        line_code="AA.O.2026.CAPEX.1.2",
        line_name="Verba Infra",
        line_order=1,
        budget_view="competence",
        movement_nature="debit",
        planned_amount=1000,
        metadata_json={"full_code": "AA.O.2026.CAPEX.1.2"},
    )
    contract = FinancialBudgetContract(
        company_id=9,
        budget_line_id=2,
        contract_code="AA.O.2026.CAPEX.1.2.3",
        name="Contrato Principal",
        status="draft",
        contract_amount=750,
        metadata_json={"full_code": "AA.O.2026.CAPEX.1.2.3"},
    )
    document = FinancialBudgetDocument(
        company_id=9,
        budget_contract_id=3,
        document_code="AA.O.2026.CAPEX.1.2.3.4",
        title="NF 1234",
        document_type="invoice",
        status="registered",
        document_amount=500,
        metadata_json={"full_code": "AA.O.2026.CAPEX.1.2.3.4"},
    )

    version_payload = version.to_dict()
    line_payload = line.to_dict()
    contract_payload = contract.to_dict()
    document_payload = document.to_dict()

    assert version_payload["code"] == "AA.O.2026.CAPEX.1"
    assert version_payload["company_id"] == 9
    assert version_payload["metadata_json"]["budget_cycle_code"] == "AA.BC.2026"
    assert version_payload["metadata_json"]["budget_category"] == "CAPEX"

    assert line_payload["line_code"] == "AA.O.2026.CAPEX.1.2"
    assert line_payload["budget_version_id"] == 1
    assert line_payload["metadata_json"]["full_code"] == "AA.O.2026.CAPEX.1.2"

    assert contract_payload["contract_code"] == "AA.O.2026.CAPEX.1.2.3"
    assert contract_payload["budget_line_id"] == 2
    assert contract_payload["metadata_json"]["full_code"] == "AA.O.2026.CAPEX.1.2.3"

    assert document_payload["document_code"] == "AA.O.2026.CAPEX.1.2.3.4"
    assert document_payload["budget_contract_id"] == 3
    assert document_payload["metadata_json"]["full_code"] == "AA.O.2026.CAPEX.1.2.3.4"


def test_create_version_enforces_company_scope_and_allows_hierarchical_budget_code(monkeypatch):
    captured = {}

    class _FakeBudgetVersion:
        company_id = _Column()
        code = _Column()
        deleted_at = _Column()

        def __init__(self, **kwargs):
            captured["kwargs"] = kwargs
            self.__dict__.update(kwargs)

        def to_dict(self):
            return dict(self.__dict__)

    duplicate_query = _QueryStub(result=_FakeBudgetVersion(
        company_id=9,
        code="AA.O.2026.CAPEX.1",
        name="Existente",
        scenario_type="original",
        status="draft",
        period_start=date(2026, 1, 1),
        period_end=date(2026, 12, 31),
    ))
    _FakeBudgetVersion.query = duplicate_query

    monkeypatch.setattr(budget_service_module, "FinancialBudgetVersion", _FakeBudgetVersion)
    monkeypatch.setattr(budget_service_module.FinancialService, "_ensure_company_scope", lambda *args, **kwargs: None)
    monkeypatch.setattr(budget_service_module.db.session, "add", lambda obj: captured.setdefault("added", obj))
    monkeypatch.setattr(budget_service_module.db.session, "commit", lambda: captured.setdefault("committed", True))
    monkeypatch.setattr(budget_service_module.db.session, "rollback", lambda: captured.setdefault("rollback", True))

    result, error = FinancialBudgetService.create_version(
        payload={
            "company_id": 9,
            "code": "AA.O.2026.CAPEX.1",
            "name": "CAPEX 2026",
            "scenario_type": "original",
            "status": "draft",
            "period_start": date(2026, 1, 1),
            "period_end": date(2026, 12, 31),
            "metadata_json": {"budget_cycle_code": "AA.BC.2026"},
        },
        allowed_company_ids=[9],
    )

    assert result is None
    assert error is not None
    assert "código" in error.lower()
    assert duplicate_query.filters, "A consulta de duplicidade deve ser executada com escopo por empresa."
    first_filter_args = duplicate_query.filters[0][0]
    assert any(arg == ("eq", 9) for arg in first_filter_args)
    assert any(arg == ("eq", "AA.O.2026.CAPEX.1") for arg in first_filter_args)

    unique_query = _QueryStub(result=None)
    _FakeBudgetVersion.query = unique_query
    captured.clear()

    result, error = FinancialBudgetService.create_version(
        payload={
            "company_id": 9,
            "code": "AA.O.2026.OPEX.1",
            "name": "OPEX 2026",
            "scenario_type": "original",
            "status": "draft",
            "period_start": date(2026, 1, 1),
            "period_end": date(2026, 12, 31),
            "metadata_json": {"budget_cycle_code": "AA.BC.2026", "budget_category": "OPEX"},
        },
        allowed_company_ids=[9],
    )

    assert error is None
    assert result is not None
    assert captured["kwargs"]["code"] == "AA.O.2026.OPEX.1"
    assert captured["kwargs"]["metadata_json"]["budget_category"] == "OPEX"
    assert captured["committed"] is True


def test_normalize_version_payload_accepts_iso_period_start_for_budget_cycle():
    payload = FinancialBudgetCodeService.normalize_version_payload(
        {
            "company_id": 9,
            "code": "AA.O.2026.CAPEX.2",
            "name": "CAPEX 2026 Extra",
            "period_start": "2026-01-01",
            "period_end": "2026-12-31",
        },
        company_id=9,
    )

    assert payload["metadata_json"]["budget_cycle"]["year"] == 2026
