"""Contas a pagar e a receber criadas via MCP exigem rateio (100%, plano de contas e centro de resultado)."""

import sys
import types
from contextlib import nullcontext
from datetime import date
from types import ModuleType, SimpleNamespace

import pytest

from services import financial_title_rules as rules
from src.core import mcp_prevalidation
from src.core.mcp_financial_tools import register_financial_mcp_tools

GOOD = [{"allocation_type": "percentage", "percentage": 100, "chart_account_id": 217, "cost_center_id": 24}]
BASE = {
    "entry_code": "TESTE-1", "entry_type": "payable", "movement_nature": "debit", "description": "TESTE título",
    "competence_date": "2026-10-13", "due_date": "2026-10-16", "original_amount": 0.01, "counterparty_id": 221,
}


# ---- formato do rateio ------------------------------------------------------------------------------
@pytest.mark.parametrize("raw", [None, [], "x", [5]])
def test_missing_or_malformed_allocations_are_refused_with_an_example(raw):
    allocations, error = rules.normalize_allocations(raw)
    assert allocations is None and error
    if raw in (None, []):
        assert "allocations" in error and "chart_account_id" in error


def test_invalid_line_is_reported_with_its_number():
    _, error = rules.normalize_allocations([{"allocation_type": "percentage"}])
    assert error.startswith("Linha 1 do rateio inválida")


def test_valid_lines_are_normalized():
    allocations, error = rules.normalize_allocations(GOOD)
    assert error is None and allocations[0]["chart_account_id"] == 217 and allocations[0]["cost_center_id"] == 24


def test_only_payable_and_receivable_require_the_rateio():
    assert rules.requires_allocations("payable") and rules.requires_allocations(" Receivable ")
    assert not rules.requires_allocations("bank_movement") and not rules.requires_allocations(None)


# ---- validação sem gravar ----------------------------------------------------------------------------
@pytest.fixture()
def stubs(monkeypatch):
    from services import financial_service as fs

    calls = {"created": 0, "rule": None}
    monkeypatch.setattr(
        fs.FinancialService,
        "validate_entry_creation",
        staticmethod(lambda **k: (SimpleNamespace(original_amount=0.01, due_date=date(2026, 10, 16)), {}, None)),
    )
    monkeypatch.setattr(
        fs.FinancialService, "create_entry", staticmethod(lambda **k: calls.__setitem__("created", calls["created"] + 1))
    )

    def fake_rule(**kwargs):
        calls["rule"] = kwargs
        return None

    monkeypatch.setattr(rules, "validate_allocations_rules", fake_rule)
    return calls


@pytest.mark.parametrize("entry_type", ["payable", "receivable"])
def test_a_title_without_the_rateio_is_refused_before_anything_is_written(stubs, entry_type):
    clean, allocations, error = rules.validate_title_creation(company_id=10, payload={**BASE, "entry_type": entry_type})
    assert clean is None and allocations is None and "allocations" in error
    assert stubs["created"] == 0


def test_a_valid_title_returns_the_payload_without_allocations_and_the_normalized_rateio(stubs):
    clean, allocations, error = rules.validate_title_creation(company_id=10, payload={**BASE, "allocations": GOOD})
    assert error is None and "allocations" not in clean and len(allocations) == 1
    assert stubs["rule"]["company_id"] == 10 and stubs["rule"]["due_date"] == date(2026, 10, 16)
    assert stubs["created"] == 0, "validar nunca grava"


def test_rule_errors_from_the_schedule_validator_are_returned(monkeypatch, stubs):
    monkeypatch.setattr(
        rules, "validate_allocations_rules", lambda **k: "A soma dos percentuais do rateio deve ser exatamente 100%."
    )
    _, _, error = rules.validate_title_creation(
        company_id=10, payload={**BASE, "allocations": [{**GOOD[0], "percentage": 60}]}
    )
    assert error == "A soma dos percentuais do rateio deve ser exatamente 100%."


def test_service_validation_errors_come_before_the_rateio_rule(monkeypatch, stubs):
    from services import financial_service as fs

    monkeypatch.setattr(
        fs.FinancialService, "validate_entry_creation", staticmethod(lambda **k: (None, None, "Já existe lançamento com código TESTE-1"))
    )
    _, _, error = rules.validate_title_creation(company_id=10, payload={**BASE, "allocations": GOOD})
    assert error.startswith("Já existe lançamento")


# ---- criação atômica -----------------------------------------------------------------------------------
def test_entry_and_rateio_are_created_together_and_a_rateio_failure_undoes_the_entry(monkeypatch):
    from services import financial_service as fs

    deleted, applied = [], []
    entry = SimpleNamespace(id=4200)
    monkeypatch.setattr(fs.FinancialService, "create_entry", staticmethod(lambda **k: (entry, None)))

    def replace(**k):
        applied.append(k["payload"])
        return (None, "Rateio inválido") if fail["on"] else ([object()], None)

    monkeypatch.setattr(fs.FinancialService, "replace_allocations", staticmethod(replace))
    fail = {"on": False}
    session = SimpleNamespace(delete=deleted.append, commit=lambda: None, rollback=lambda: None)
    monkeypatch.setattr("models.db", SimpleNamespace(session=session))
    row = SimpleNamespace(id=4200)
    fake_entry_model = SimpleNamespace(
        company_id=0, id=0, query=SimpleNamespace(filter=lambda *a, **k: SimpleNamespace(first=lambda: row))
    )
    monkeypatch.setattr("models.financial.FinancialEntry", fake_entry_model)

    allocations, _ = rules.normalize_allocations(GOOD)
    created, error = rules.create_title_with_allocations(payload={**BASE, "company_id": 10}, allocations=allocations)
    assert error is None and created is entry and deleted == []
    sent = applied[0]
    assert sent["financial_entry_id"] == 4200 and sent["allocations"][0]["chart_account_id"] == 217
    assert sent["allocations"][0]["company_id"] == 10

    fail["on"] = True
    created, error = rules.create_title_with_allocations(payload={**BASE, "company_id": 10}, allocations=allocations)
    assert created is None and error == "Rateio inválido"
    assert deleted == [row], "o lançamento recém-criado é desfeito quando o rateio falha"


# ---- ferramenta MCP e pré-validador -----------------------------------------------------------------------
class _FakeMCP:
    def __init__(self):
        self.registered = {}

    def tool(self, *args, **kwargs):
        def decorate(fn):
            self.registered[fn.__name__] = fn
            return fn

        return decorate


@pytest.fixture()
def tool(monkeypatch):
    seen = {}
    monkeypatch.setitem(
        sys.modules, "app", types.SimpleNamespace(create_app=lambda: types.SimpleNamespace(app_context=lambda: nullcontext()))
    )
    fake_service = ModuleType("services.financial_service")
    fake_service.FinancialService = SimpleNamespace(
        create_entry=staticmethod(lambda *, payload: seen.__setitem__("plain", payload) or (object(), None)),
        serialize_entry=staticmethod(lambda entry, **k: {"id": 1}),
    )
    monkeypatch.setitem(sys.modules, "services.financial_service", fake_service)
    context = types.SimpleNamespace(user_id=14, company_id=10, employee_id=None, channel="mcp_http", thread_id=None, metadata={})
    monkeypatch.setattr("src.intelligence.tool_context.get_sapiens_context", lambda: context)
    monkeypatch.setattr(
        rules,
        "validate_title_creation",
        lambda *, company_id, payload: (
            {k: v for k, v in payload.items() if k != "allocations"},
            rules.normalize_allocations(payload.get("allocations"))[0],
            None if payload.get("allocations") else rules.ALLOCATIONS_REQUIRED_MESSAGE,
        ),
    )
    monkeypatch.setattr(
        rules, "create_title_with_allocations", lambda *, payload, allocations: seen.update(atomic=(payload, allocations)) or (object(), None)
    )
    mcp = _FakeMCP()
    register_financial_mcp_tools(mcp)
    return mcp.registered["create_financial_entry"], seen


REFUSAL = "Conta a pagar/receber deve ser criada como agendamento. Use create_financial_schedule_secure."


def test_a_payable_is_refused_by_the_tool_even_without_the_rateio(tool):
    create, seen = tool
    result = create(10, dict(BASE))
    assert result == {"success": False, "error": REFUSAL}
    assert "atomic" not in seen and "plain" not in seen


def test_a_payable_is_refused_by_the_tool_even_with_the_rateio(tool):
    create, seen = tool
    result = create(10, {**BASE, "allocations": GOOD})
    assert result == {"success": False, "error": REFUSAL}
    assert "atomic" not in seen and "plain" not in seen


def test_other_entry_types_keep_the_previous_behavior(tool):
    create, seen = tool
    result = create(10, {**BASE, "entry_type": "bank_movement"})
    assert result["success"] is True and "plain" in seen and "atomic" not in seen


def test_prevalidator_runs_the_same_rule_and_skips_types_without_the_requirement(monkeypatch):
    calls = []
    monkeypatch.setattr(
        rules, "validate_title_creation", lambda *, company_id, payload: calls.append(payload) or (None, None, "erro de rateio")
    )
    refused = mcp_prevalidation.financial_entry({"company_id": 10, "payload": dict(BASE)})
    assert refused == "Conta a pagar/receber deve ser criada como agendamento. Use create_financial_schedule_secure."
    assert not calls
    with_allocations = {**BASE, "entry_type": "bank_movement", "allocations": [{"allocation_type": "percentage", "percentage": 100}]}
    assert mcp_prevalidation.financial_entry({"company_id": 10, "payload": with_allocations}) == "erro de rateio"
    assert calls[0]["company_id"] == 10
    assert mcp_prevalidation.financial_entry({"company_id": 10, "payload": {**BASE, "entry_type": "bank_movement"}}) is None
    forged = mcp_prevalidation.financial_entry({"company_id": 10, "payload": {**BASE, "company_id": 11}})
    assert forged.startswith("company_id do payload diverge")
    assert "create_financial_entry" in mcp_prevalidation.PREVALIDATORS
