"""Regra D6 (opção B): quais mutações do mcp-versus exigem aprovação humana persistida, e que o runtime a aplica."""
from __future__ import annotations

import sys
from contextlib import nullcontext
from types import ModuleType, SimpleNamespace

import pytest

from src.core.mcp_gate_policy import APPROVAL_TOOLS, requires_persisted_approval
from src.core.mcp_runtime import wrap_mcp_callable


def _cap(risk="medium", gate=False):
    return SimpleNamespace(risk=SimpleNamespace(value=risk), human_gate=gate)


# ---- a regra ----------------------------------------------------------------------------------
@pytest.mark.parametrize(
    "name",
    [
        "delete_meeting_topic", "delete_meeting_decision", "delete_meeting_activity", "remove_commercial_fiscal_batch",
        "cancel_commercial_billing", "reset_something", "archive_something",
        "approve_work_journey_absence_request_tool", "reject_something",
        "publish_whatsapp_status_art", "resume_whatsapp_status_schedule", "send_meeting_minutes",
    ],
)
def test_destructive_approval_and_external_classes_require_approval(name):
    assert requires_persisted_approval(name, _cap()) is True


@pytest.mark.parametrize("name", sorted(APPROVAL_TOOLS))
def test_financial_value_and_contract_lifecycle_tools_require_approval(name):
    assert requires_persisted_approval(name, _cap()) is True


@pytest.mark.parametrize(
    "name",
    [
        "create_meeting", "update_meeting", "start_meeting", "finish_meeting", "schedule_meeting",
        "create_project_task_secure", "update_project_task_secure", "create_macro_process",
        "upsert_strategy_identity_tool", "create_commercial_contract", "update_commercial_contract_general",
        "create_whatsapp_status_schedule", "pause_whatsapp_status_schedule", "sync_plan_participants_tool",
    ],
)
def test_ordinary_create_and_edit_do_not_require_approval(name):
    assert requires_persisted_approval(name, _cap(gate=True)) is False, "flag declarativo não basta (D6)"


@pytest.mark.parametrize("name", ["list_meetings", "get_meeting", "search_organizational_knowledge_secure", "describe_x"])
def test_reads_never_require_approval(name):
    assert requires_persisted_approval(name, _cap(risk="high", gate=True)) is False


def test_high_risk_gated_mutation_requires_approval_but_ungated_does_not_by_flag_alone():
    assert requires_persisted_approval("update_thing", _cap(risk="high", gate=True)) is True
    assert requires_persisted_approval("update_thing", _cap(risk="high", gate=False)) is False


def test_the_meeting_deletions_are_covered_by_the_rule_in_the_real_catalog():
    from src.intelligence.tool_catalog import catalog

    for name in ("delete_meeting_topic", "delete_meeting_decision", "delete_meeting_activity"):
        assert requires_persisted_approval(name, catalog.get_tool_capability(name)) is True


# ---- o runtime aplica a regra (mesmo quando a política aprovaria) ----------------------------
def _runtime(monkeypatch, *, capability, approval_allowed):
    fake_app_module = ModuleType("app")

    class _App:
        def app_context(self):
            return nullcontext()

    fake_app_module.create_app = lambda: _App()
    monkeypatch.setitem(sys.modules, "app", fake_app_module)
    fake_catalog = ModuleType("src.intelligence.tool_catalog")
    fake_catalog.catalog = SimpleNamespace(get_tool_capability=lambda name: capability)
    monkeypatch.setitem(sys.modules, "src.intelligence.tool_catalog", fake_catalog)

    context = SimpleNamespace(
        user_id=3, principal_id=71, company_id=9, employee_id=23, role="administrador", channel="mcp",
        thread_id=None, permissions=(), accessible_company_ids=(9,), metadata={"surface": "user", "principal_id": 71},
    )
    monkeypatch.setattr("src.core.mcp_runtime.resolve_mcp_execution_context", lambda payload, **k: context)
    monkeypatch.setattr(
        "src.core.mcp_runtime.evaluate_tool_policy",
        lambda source, request: SimpleNamespace(allowed=True, reason="ok"),
    )
    seen = {"final_confirmed": None, "requested": None}
    monkeypatch.setattr("src.core.mcp_runtime._emit_mcp_policy_audit", lambda *a, **k: None)
    monkeypatch.setattr(
        "src.core.mcp_runtime.require_tool_policy",
        lambda source, request: seen.__setitem__("final_confirmed", request.confirmed_mutation),
    )
    monkeypatch.setattr(
        "services.tool_approval_service.tool_approval_service",
        SimpleNamespace(
            authorize_and_consume=lambda binding: SimpleNamespace(
                allowed=approval_allowed, approval_request_id=91, reason="aprovação persistida vigente não encontrada"
            )
        ),
    )
    monkeypatch.setattr(
        "services.tool_approval_service.tool_approval_request_service",
        SimpleNamespace(
            request=lambda binding, **kw: seen.__setitem__("requested", kw)
            or SimpleNamespace(approval_request_id=321, reused_existing=False)
        ),
    )
    return seen


def _tool(name, calls):
    def tool(**kwargs):
        calls.append(kwargs)
        return {"ok": True}

    tool.__name__ = name
    tool.__app32_tool_name__ = name
    return tool


def test_destructive_medium_risk_tool_asks_for_approval_and_does_not_run(monkeypatch):
    seen = _runtime(monkeypatch, capability=SimpleNamespace(domain="meetings", risk=SimpleNamespace(value="medium"), human_gate=True, permissions=(), required_context=()), approval_allowed=False)
    calls = []
    with pytest.raises(PermissionError, match="solicitação #321"):
        wrap_mcp_callable(_tool("delete_meeting_topic", calls))(company_id=9, meeting_id=1, topic_id="t")
    assert calls == [] and "classe de mutação" in seen["requested"]["reason"]


def test_destructive_medium_risk_tool_runs_after_the_persisted_approval(monkeypatch):
    seen = _runtime(monkeypatch, capability=SimpleNamespace(domain="meetings", risk=SimpleNamespace(value="medium"), human_gate=True, permissions=(), required_context=()), approval_allowed=True)
    calls = []
    out = wrap_mcp_callable(_tool("delete_meeting_topic", calls))(company_id=9, meeting_id=1, topic_id="t")
    assert out == {"ok": True} and len(calls) == 1 and seen["final_confirmed"] is True


def test_ordinary_edit_runs_without_approval_even_if_the_catalog_flag_is_set(monkeypatch):
    seen = _runtime(monkeypatch, capability=SimpleNamespace(domain="meetings", risk=SimpleNamespace(value="medium"), human_gate=True, permissions=(), required_context=()), approval_allowed=False)
    calls = []
    out = wrap_mcp_callable(_tool("update_meeting", calls))(company_id=9, meeting_id=1)
    assert out == {"ok": True} and len(calls) == 1 and seen["requested"] is None and seen["final_confirmed"] is False
