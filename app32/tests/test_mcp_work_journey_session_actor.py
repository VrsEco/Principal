"""Jornada de trabalho no mcp-versus: solicitante e aprovador vêm da sessão, nunca do cliente (M2)."""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from mcp.server.fastmcp import FastMCP

import src.core.mcp_work_journey_tools as tools_module

SESSION_USER = 42
IDENTITY_PARAMS = {"user_id", "approver_user_id", "requested_by_user_id", "actor_user_id"}
ACTOR_TOOLS = [
    "create_work_journey_transfer_request_tool",
    "approve_work_journey_transfer_request_tool",
    "create_work_journey_absence_request_tool",
    "approve_work_journey_absence_request_tool",
    "lock_work_journey_agenda_tool",
]


@pytest.fixture
def server(monkeypatch):
    calls = {}

    monkeypatch.setattr(tools_module, "_run", lambda callback, *a, **k: callback(*a, **k))

    context = SimpleNamespace(user_id=SESSION_USER, company_id=9, role="administrador", employee_id=None)

    def fake_ensure(*, company_id, employee_id, payload=None):
        calls["ensure"] = {"company_id": company_id, "employee_id": employee_id}
        return 9, context

    monkeypatch.setattr(tools_module, "ensure_employee_mutation_allowed", fake_ensure)
    monkeypatch.setattr("src.core.mcp_runtime.resolve_mcp_execution_context", lambda payload=None, **k: context)

    def recorder(name):
        def _fn(*args):
            calls[name] = args
            return {"ok": name}

        return _fn

    for service in ("create_transfer_request", "approve_transfer_request", "create_absence_request", "approve_absence_request", "lock_work_journey_agenda"):
        monkeypatch.setattr(tools_module, service, recorder(service))
    monkeypatch.setattr(tools_module, "WorkJourneyItem", SimpleNamespace(query=SimpleNamespace(filter_by=lambda **k: SimpleNamespace(first=lambda: SimpleNamespace(employee_id=7)))))

    mcp = FastMCP("probe")
    tools_module.register_work_journey_tools(mcp)
    return SimpleNamespace(manager=mcp._tool_manager, calls=calls)


@pytest.mark.parametrize("name", ACTOR_TOOLS)
def test_actor_tools_expose_no_identity_parameter(server, name):
    props = set(server.manager.get_tool(name).parameters["properties"])
    assert props.isdisjoint(IDENTITY_PARAMS), f"{name} ainda aceita identidade do cliente: {props & IDENTITY_PARAMS}"
    assert "company_id" in props


def test_transfer_request_is_attributed_to_the_session_user(server):
    server.manager.get_tool("create_work_journey_transfer_request_tool").fn(company_id=9, item_id=3, to_employee_id=8, reason="x")
    args = server.calls["create_transfer_request"]
    assert args[-1] == SESSION_USER
    assert server.calls["ensure"]["employee_id"] == 7, "o colaborador dono da tarefa é conferido contra a sessão"


def test_transfer_approval_uses_the_session_user_as_approver(server):
    server.manager.get_tool("approve_work_journey_transfer_request_tool").fn(company_id=9, request_id=5, resolution_notes="ok")
    company_id, request_id, approver, notes = server.calls["approve_transfer_request"]
    assert (company_id, request_id, approver, notes) == (9, 5, SESSION_USER, "ok")


def test_absence_request_is_attributed_to_the_session_user_and_checks_the_employee(server):
    payload = {"employee_id": 7, "absence_type": "vacation", "start_date": "2026-11-01", "end_date": "2026-11-10"}
    server.manager.get_tool("create_work_journey_absence_request_tool").fn(company_id=9, payload=payload)
    assert server.calls["create_absence_request"][-1] == SESSION_USER
    assert server.calls["ensure"]["employee_id"] == 7


def test_absence_approval_uses_the_session_user_as_approver(server):
    server.manager.get_tool("approve_work_journey_absence_request_tool").fn(company_id=9, request_id=6)
    assert server.calls["approve_absence_request"][:3] == (9, 6, SESSION_USER)


def test_agenda_lock_is_attributed_to_the_session_user(server):
    server.manager.get_tool("lock_work_journey_agenda_tool").fn(company_id=9, employee_id=7, anchor_date="2026-10-09")
    assert server.calls["lock_work_journey_agenda"][-1] == SESSION_USER


def test_session_without_a_user_cannot_approve(server, monkeypatch):
    monkeypatch.setattr("src.core.mcp_runtime.resolve_mcp_execution_context", lambda payload=None, **k: SimpleNamespace(user_id=None, company_id=9))
    with pytest.raises(PermissionError):
        server.manager.get_tool("approve_work_journey_transfer_request_tool").fn(company_id=9, request_id=5)
