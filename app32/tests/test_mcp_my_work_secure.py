"""list_my_work_secure: minhas atividades por empresa, tenant-safe e somente leitura."""
from __future__ import annotations

import asyncio
from datetime import date

import pytest
from mcp.server.fastmcp import FastMCP

import src.core.mcp_my_work_tools as my_work
from src.intelligence.tool_catalog import catalog

TODAY = date(2026, 10, 8)


def _act(kind, ident, company_id=9, mine=True, deadline="2026-10-07", status="pending", **extra):
    return {
        "type": kind,
        "id": ident,
        "company_id": company_id,
        "title": f"{kind} {ident}",
        "deadline_date": deadline,
        "status": status,
        "is_overdue": deadline < TODAY.isoformat(),
        "viewer_is_directly_assigned": mine,
        **extra,
    }


@pytest.fixture
def fake_service(monkeypatch):
    calls = []

    def _install(activities, as_tuple=True):
        def fake(**kwargs):
            calls.append(kwargs)
            return (activities, {"me": len(activities)}) if as_tuple else activities

        monkeypatch.setattr("services.my_work.discovery_service.get_user_activities_v2", fake)
        return calls

    return _install


def test_capability_is_a_low_risk_tenant_scoped_read():
    capability = catalog.get_tool_capability("list_my_work_secure")
    assert capability is not None and capability.domain == "routine"
    assert getattr(capability.risk, "value", capability.risk) == "low"
    assert capability.human_gate is False
    assert set(capability.required_context) == {"user", "company"}
    assert "mcp_user" in capability.scopes


def test_only_my_directly_assigned_items_of_the_requested_company(fake_service):
    calls = fake_service([
        _act("project", 1, mine=True),
        _act("project", 2, mine=False),                    # da empresa, mas de outra pessoa
        _act("process", 3, mine=True),
        _act("project", 4, company_id=1, mine=True),       # outra empresa
    ])
    out = my_work.build_my_work(user_id=3, company_id=9, due="today", limit=50, today=TODAY)
    assert [(i["type"], i["id"]) for i in out["items"]] == [("process_instance", 3), ("project_task", 1)]
    assert out["company_id"] == 9 and out["summary"]["total"] == 2
    call = calls[0]
    assert call["scope"] == "me" and call["company_ids"] == [9] and call["active_company_id"] == 9 and call["user_id"] == 3


def test_client_role_company_scope_still_returns_only_mine(fake_service):
    """O serviço força scope=company para o papel cliente; o filtro final mantém só o que é meu."""
    fake_service([_act("project", 10, mine=False), _act("process", 11, mine=False), _act("project", 12, mine=True)])
    out = my_work.build_my_work(user_id=3, company_id=9, due="open", limit=50, today=TODAY)
    assert [i["id"] for i in out["items"]] == [12]


def test_due_today_applies_deadline_filter_and_open_does_not(fake_service):
    calls = fake_service([])
    my_work.build_my_work(user_id=3, company_id=9, due="today", limit=10, today=TODAY)
    my_work.build_my_work(user_id=3, company_id=9, due="open", limit=10, today=TODAY)
    assert calls[0]["filters"] == {"delivery_tags": ["open"], "due_date_end": "2026-10-08"}
    assert calls[1]["filters"] == {"delivery_tags": ["open"]}


def test_summary_overdue_ordering_and_limit(fake_service):
    fake_service([
        _act("project", 1, deadline="2026-10-09"),
        _act("process", 2, deadline="2026-10-01"),
        _act("project", 3, deadline="2026-10-05"),
        _act("project", 4, deadline="2026-10-08"),
    ])
    out = my_work.build_my_work(user_id=3, company_id=9, due="open", limit=2, today=TODAY)
    assert out["summary"] == {"total": 4, "overdue": 2, "project_tasks": 3, "process_instances": 1}
    assert out["returned"] == 2 and out["limit"] == 2
    assert [i["id"] for i in out["items"]] == [2, 3]  # mais antigas primeiro


def test_accepts_plain_list_return_and_empty_result(fake_service):
    fake_service([_act("project", 1)], as_tuple=False)
    assert my_work.build_my_work(user_id=3, company_id=9, due="open", limit=5, today=TODAY)["summary"]["total"] == 1
    fake_service([])
    out = my_work.build_my_work(user_id=3, company_id=9, due="open", limit=5, today=TODAY)
    assert out["items"] == [] and out["summary"]["total"] == 0


@pytest.mark.parametrize("limit", [0, -1, 101, True, "10", None])
def test_invalid_limit_is_rejected(limit):
    with pytest.raises(ValueError):
        my_work._validated_limit(limit)


@pytest.mark.parametrize("due", ["week", "", None, "ALL"])
def test_invalid_due_is_rejected(due):
    with pytest.raises(ValueError):
        my_work._validated_due(due)


def test_registered_tool_requires_an_authenticated_user(monkeypatch):
    server = FastMCP("probe")
    my_work.register_my_work_mcp_tools(server)
    fn = server._tool_manager.get_tool("list_my_work_secure").fn
    monkeypatch.setattr("src.intelligence.tools_support.get_active_user_id", lambda: None)
    with pytest.raises(PermissionError):
        fn(company_id=9)


def test_registered_tool_uses_the_authenticated_user_not_a_parameter(monkeypatch, fake_service):
    calls = fake_service([])
    server = FastMCP("probe")
    my_work.register_my_work_mcp_tools(server)
    tool = server._tool_manager.get_tool("list_my_work_secure")
    assert "user_id" not in tool.parameters["properties"], "o usuário nunca pode vir do cliente"
    monkeypatch.setattr("src.intelligence.tools_support.get_active_user_id", lambda: 7)
    tool.fn(company_id=9, due="open", limit=5)
    assert calls[0]["user_id"] == 7


def test_registrar_exposes_exactly_one_read_tool():
    server = FastMCP("probe")
    my_work.register_my_work_mcp_tools(server)
    names = {tool.name for tool in asyncio.run(FastMCP.list_tools(server))}
    assert names == {"list_my_work_secure"}
