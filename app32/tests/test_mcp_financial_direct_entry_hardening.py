"""Lançamento direto via MCP: pré-validação antes da aprovação, autor/aprovação gravados e resposta compacta."""

import sys
import types
from contextlib import nullcontext
from datetime import datetime
from types import ModuleType, SimpleNamespace

import pytest

from services.financial_direct_entry_service import FinancialDirectEntryService
from src.core import mcp_prevalidation
from src.core.mcp_financial_tools import _compact_direct_entry_result, register_financial_mcp_tools
from src.core.mcp_runtime import _IdempotencyState, wrap_mcp_callable


# ---- runtime: a pré-validação roda antes de pedir ou consumir a aprovação ---------------------------
def _runtime(monkeypatch, *, approval_allowed=False):
    fake_app_module = ModuleType("app")

    class _App:
        def app_context(self):
            return nullcontext()

    fake_app_module.create_app = lambda: _App()
    monkeypatch.setitem(sys.modules, "app", fake_app_module)
    capability = SimpleNamespace(
        domain="finance", risk=SimpleNamespace(value="medium"), human_gate=True, permissions=(), required_context=()
    )
    fake_catalog = ModuleType("src.intelligence.tool_catalog")
    fake_catalog.catalog = SimpleNamespace(get_tool_capability=lambda name: capability)
    monkeypatch.setitem(sys.modules, "src.intelligence.tool_catalog", fake_catalog)
    context = SimpleNamespace(
        user_id=3, principal_id=71, company_id=10, employee_id=23, role="administrador", channel="mcp",
        thread_id=None, permissions=(), accessible_company_ids=(10,), metadata={"surface": "finance", "principal_id": 71},
    )
    monkeypatch.setattr("src.core.mcp_runtime.resolve_mcp_execution_context", lambda payload, **k: context)
    monkeypatch.setattr(
        "src.core.mcp_runtime.evaluate_tool_policy", lambda source, request: SimpleNamespace(allowed=True, reason="ok")
    )
    monkeypatch.setattr("src.core.mcp_runtime._emit_mcp_policy_audit", lambda *a, **k: None)
    monkeypatch.setattr("src.core.mcp_runtime.require_tool_policy", lambda source, request: None)
    # A camada de idempotência tem testes próprios (tests/test_mcp_idempotency.py); aqui só a pré-validação.
    monkeypatch.setattr("src.core.mcp_runtime._idempotency_precheck", lambda *a, **k: _IdempotencyState())
    monkeypatch.setattr("src.core.mcp_runtime._idempotency_claim", lambda *a, **k: (None, None))
    seen = {"approval_requested": 0, "consumed": 0}

    def authorize(binding):
        seen["consumed"] += 1
        return SimpleNamespace(allowed=approval_allowed, approval_request_id=91, reason="sem aprovação")

    monkeypatch.setattr(
        "services.tool_approval_service.tool_approval_service", SimpleNamespace(authorize_and_consume=authorize)
    )
    monkeypatch.setattr(
        "services.tool_approval_service.tool_approval_request_service",
        SimpleNamespace(
            request=lambda binding, **kw: seen.__setitem__("approval_requested", seen["approval_requested"] + 1)
            or SimpleNamespace(approval_request_id=321, reused_existing=False)
        ),
    )
    return seen


def _tool(calls):
    def create_financial_direct_entry(**kwargs):
        calls.append(kwargs)
        return {"success": True}

    create_financial_direct_entry.__app32_tool_name__ = "create_financial_direct_entry"
    return create_financial_direct_entry


def test_business_error_is_returned_before_any_approval_is_requested_or_consumed(monkeypatch):
    seen = _runtime(monkeypatch)
    monkeypatch.setitem(
        mcp_prevalidation.PREVALIDATORS, "create_financial_direct_entry", "tests_prevalidator_stub:fail"
    )
    stub = ModuleType("tests_prevalidator_stub")
    stub.fail = lambda arguments: "Selecione a conta bancária do lançamento rápido."
    monkeypatch.setitem(sys.modules, "tests_prevalidator_stub", stub)
    calls = []
    result = wrap_mcp_callable(_tool(calls))(company_id=10, payload={"entry_type": "payable"}, idempotency_key="k1")
    assert result == {"success": False, "error": "Selecione a conta bancária do lançamento rápido.", "prevalidated": True}
    assert calls == [] and seen == {"approval_requested": 0, "consumed": 0}


def test_valid_content_still_asks_for_the_approval(monkeypatch):
    seen = _runtime(monkeypatch)
    stub = ModuleType("tests_prevalidator_stub")
    stub.ok = lambda arguments: None
    monkeypatch.setitem(sys.modules, "tests_prevalidator_stub", stub)
    monkeypatch.setitem(mcp_prevalidation.PREVALIDATORS, "create_financial_direct_entry", "tests_prevalidator_stub:ok")
    calls = []
    with pytest.raises(PermissionError, match="solicitação #321"):
        wrap_mcp_callable(_tool(calls))(company_id=10, payload={"entry_type": "payable"}, idempotency_key="k2")
    assert calls == [] and seen["approval_requested"] == 1


def test_a_failing_prevalidator_is_ignored_and_never_blocks(monkeypatch):
    stub = ModuleType("tests_prevalidator_stub")

    def boom(arguments):
        raise RuntimeError("banco indisponível")

    stub.boom = boom
    monkeypatch.setitem(sys.modules, "tests_prevalidator_stub", stub)
    monkeypatch.setitem(mcp_prevalidation.PREVALIDATORS, "create_financial_direct_entry", "tests_prevalidator_stub:boom")
    assert mcp_prevalidation.prevalidate("create_financial_direct_entry", {"company_id": 10, "payload": {}}) is None
    assert mcp_prevalidation.prevalidate("ferramenta_sem_prevalidador", {}) is None


# ---- serviço: validação sem efeito colateral -----------------------------------------------------------
BASE = {
    "company_id": 10, "entry_type": "payable", "description": "TESTE lançamento", "counterparty_id": 221,
    "competence_date": "2026-10-12", "occurred_on": "2026-10-12", "original_amount": "0.01",
}


@pytest.fixture()
def service_stubs(monkeypatch):
    from services import financial_direct_entry_service as module

    monkeypatch.setattr(module.FinancialService, "_ensure_company_scope", staticmethod(lambda *a, **k: None))
    monkeypatch.setattr(FinancialDirectEntryService, "_apply_counterparty_defaults", staticmethod(lambda **k: None))
    monkeypatch.setattr(module.FinancialCatalogService, "validate_reference_ids", staticmethod(lambda **k: None))
    monkeypatch.setattr(module.FinancialScheduleService, "_validate_schedule_allocations", staticmethod(lambda **k: None))
    monkeypatch.setattr(FinancialDirectEntryService, "_validate_enabled_domains", staticmethod(lambda **k: None))
    created = []
    monkeypatch.setattr(
        module.FinancialScheduleService, "create_schedule", staticmethod(lambda **k: created.append(k) or ({"id": 1}, None))
    )
    return created


def test_validation_requires_the_bank_account_and_never_writes(service_stubs):
    data, error = FinancialDirectEntryService.validate_direct_entry(payload=dict(BASE))
    assert data is None and "conta bancária" in error
    assert service_stubs == []


def test_validation_passes_through_allocation_errors_and_returns_the_data_when_valid(monkeypatch, service_stubs):
    from services import financial_direct_entry_service as module

    monkeypatch.setattr(
        module.FinancialScheduleService,
        "_validate_schedule_allocations",
        staticmethod(lambda **k: "Informe ao menos uma linha de rateio para o agendamento."),
    )
    data, error = FinancialDirectEntryService.validate_direct_entry(payload={**BASE, "bank_account_id": 16})
    assert data is None and "rateio" in error

    monkeypatch.setattr(module.FinancialScheduleService, "_validate_schedule_allocations", staticmethod(lambda **k: None))
    data, error = FinancialDirectEntryService.validate_direct_entry(payload={**BASE, "bank_account_id": 16})
    assert error is None and data.bank_account_id == 16
    assert service_stubs == [], "validar nunca cria o agendamento"


def test_prevalidator_for_direct_entry_binds_the_tenant_and_reports_the_service_error(monkeypatch, service_stubs):
    assert "conta bancária" in mcp_prevalidation.direct_entry({"company_id": 10, "payload": dict(BASE)})
    assert mcp_prevalidation.direct_entry({"company_id": 10, "payload": {**BASE, "company_id": 11}}).startswith(
        "company_id do payload diverge"
    )
    assert mcp_prevalidation.direct_entry({"company_id": 10, "payload": {**BASE, "bank_account_id": 16}}) is None
    assert service_stubs == []


# ---- ferramenta: autor, aprovação e resposta compacta ----------------------------------------------------
class _FakeMCP:
    def __init__(self):
        self.registered = {}

    def tool(self, *args, **kwargs):
        def decorate(fn):
            self.registered[fn.__name__] = fn
            return fn

        return decorate


def _install(monkeypatch, *, gate_metadata, approval_action):
    captured = {}
    monkeypatch.setattr(
        FinancialDirectEntryService,
        "create_direct_entry",
        staticmethod(
            lambda *, payload, allowed_company_ids=None: captured.__setitem__("payload", payload)
            or (
                {
                    "schedule": {"id": 2940, "schedule_code": "AG-1", "status": "completed", "metadata_json": {"x": 1}},
                    "entry": {"id": 4150, "entry_code": "DIR-1", "status": "settled", "allocations": [{"id": 1}], "settlements": [{}]},
                    "settlement": {"id": 4324, "settlement_code": "BX-1", "settlement_status": "posted", "net_amount": 0.01, "settlement_components": [1, 2]},
                },
                None,
            )
        ),
    )

    class _Query:
        def filter_by(self, **kwargs):
            captured["approval_filter"] = kwargs
            return self

        def first(self):
            return approval_action

    fake_agent_action = ModuleType("models.agent_action")
    fake_agent_action.AgentAction = SimpleNamespace(query=_Query())
    monkeypatch.setitem(sys.modules, "models.agent_action", fake_agent_action)
    context = types.SimpleNamespace(
        user_id=14, company_id=10, employee_id=88, channel="mcp_http", thread_id=None, metadata=gate_metadata
    )
    monkeypatch.setattr("src.intelligence.tool_context.get_sapiens_context", lambda: context)
    monkeypatch.setitem(sys.modules, "app", types.SimpleNamespace(create_app=lambda: types.SimpleNamespace(app_context=lambda: nullcontext())))
    return captured


def test_the_author_and_the_consumed_approval_are_recorded_and_cannot_be_forged(monkeypatch):
    approved_at = datetime(2026, 10, 12, 8, 55, 0)
    action = SimpleNamespace(id=940, status="executed", resolved_at=approved_at, payload={"approved_by_user_id": 14})
    captured = _install(monkeypatch, gate_metadata={"approved_human_gate_request_id": 940}, approval_action=action)
    mcp = _FakeMCP()
    register_financial_mcp_tools(mcp)
    response = mcp.registered["create_financial_direct_entry"](
        10,
        {
            **BASE,
            "bank_account_id": 16,
            "created_by_user_id": 999,
            "created_by_agent": "forjado",
            "metadata_json": {"human_approval": {"approved_by_user_id": 999}, "nota": "ok"},
        },
    )
    assert response["success"] is True
    payload = captured["payload"]
    assert payload["created_by_user_id"] == 14, "o autor vem da sessão, nunca do cliente"
    assert payload["created_by_agent"] != "forjado"
    assert payload["metadata_json"]["nota"] == "ok"
    assert payload["metadata_json"]["human_approval"] == {
        "request_id": 940, "approved_by_user_id": 14, "approved_at": approved_at.isoformat(),
    }
    assert payload["metadata_json"]["audit"]["actor"]["user_id"] == 14


def test_without_a_consumed_approval_no_approval_is_recorded_even_if_the_client_forges_one(monkeypatch):
    captured = _install(monkeypatch, gate_metadata={}, approval_action=None)
    mcp = _FakeMCP()
    register_financial_mcp_tools(mcp)
    mcp.registered["create_financial_direct_entry"](
        10, {**BASE, "bank_account_id": 16, "metadata_json": {"human_approval": {"approved_by_user_id": 999}}}
    )
    assert "human_approval" not in captured["payload"]["metadata_json"]


def test_the_response_is_compact(monkeypatch):
    _install(monkeypatch, gate_metadata={}, approval_action=None)
    mcp = _FakeMCP()
    register_financial_mcp_tools(mcp)
    response = mcp.registered["create_financial_direct_entry"](10, {**BASE, "bank_account_id": 16})
    assert response["success"] is True
    assert response["schedule"] == {"id": 2940, "schedule_code": "AG-1", "status": "completed"}
    assert response["entry"]["id"] == 4150 and "allocations" not in response["entry"] and "settlements" not in response["entry"]
    assert response["settlement"]["settlement_code"] == "BX-1" and "settlement_components" not in response["settlement"]
    assert "get_financial_entry" in response["detail"]


def test_compacting_tolerates_an_empty_result():
    assert _compact_direct_entry_result(None)["entry"] == {}


def test_approved_entries_carry_the_approver_into_the_entry_payload():
    fields = FinancialDirectEntryService._approval_fields(
        {"human_approval": {"request_id": 940, "approved_by_user_id": 14, "approved_at": "2026-10-12T08:55:00"}}
    )
    assert fields == {"approved_by_user_id": 14, "approved_at": datetime(2026, 10, 12, 8, 55, 0)}
    assert FinancialDirectEntryService._approval_fields({}) == {}
    assert FinancialDirectEntryService._approval_fields({"human_approval": {"approved_by_user_id": True}}) == {}
    assert FinancialDirectEntryService._approval_fields({"human_approval": {"approved_by_user_id": 14, "approved_at": "lixo"}}) == {
        "approved_by_user_id": 14
    }
