"""list_my_work_all_companies: minhas atividades em todas as empresas com grant, validadas uma a uma."""
from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pytest
from mcp.server.fastmcp import FastMCP

import src.core.mcp_my_work_tools as my_work

TODAY = date(2026, 10, 8)


def _act(kind, ident, company_id, deadline="2026-10-07", mine=True):
    return {
        "type": kind,
        "id": ident,
        "company_id": company_id,
        "title": f"{kind} {ident}",
        "deadline_date": deadline,
        "status": "pending",
        "is_overdue": deadline < TODAY.isoformat(),
        "viewer_is_directly_assigned": mine,
    }


@pytest.fixture
def service(monkeypatch):
    calls = []
    data = {
        9: [_act("project", 1, 9, "2026-10-01"), _act("process", 2, 9, "2026-10-08")],
        1: [_act("project", 3, 1, "2026-09-30"), _act("project", 4, 1, mine=False)],
        3: [_act("project", 5, 3, "2026-10-02")],
        2: [],
    }

    def fake(**kwargs):
        calls.append(kwargs)
        return (data[kwargs["company_ids"][0]], {})

    monkeypatch.setattr("services.my_work.discovery_service.get_user_activities_v2", fake)
    return SimpleNamespace(calls=calls)


def _build(service, ids, validate=lambda cid: True, names=None, due="open", limit=50):
    return my_work.build_my_work_all_companies(
        user_id=3,
        company_ids=tuple(ids),
        validate_company=validate,
        company_names=names or {9: "AA", 1: "AL", 3: "AI", 2: "AB"},
        due=due,
        limit=limit,
        today=TODAY,
    )


def test_aggregates_only_my_items_across_companies_sorted_oldest_first(service):
    out = _build(service, [9, 1, 3])
    assert [(i["company_id"], i["id"]) for i in out["items"]] == [(1, 3), (9, 1), (3, 5), (9, 2)]
    assert out["summary"] == {"total": 4, "overdue": 3, "companies_scanned": 3, "companies_with_items": 3, "companies_skipped": 0}
    assert all(i["company_name"] for i in out["items"])


def test_each_company_is_queried_alone_for_the_authenticated_user(service):
    _build(service, [9, 1])
    assert [c["company_ids"] for c in service.calls] == [[1], [9]]
    assert all(c["scope"] == "me" and c["user_id"] == 3 for c in service.calls)
    assert [c["active_company_id"] for c in service.calls] == [1, 9]


def test_denied_companies_are_skipped_and_never_read(service):
    out = _build(service, [9, 1, 3], validate=lambda cid: cid != 1)
    assert {i["company_id"] for i in out["items"]} == {9, 3}
    assert out["summary"]["companies_skipped"] == 1
    assert all(c["company_ids"] != [1] for c in service.calls)


def test_permission_error_from_validation_counts_as_denied(service):
    def validate(cid):
        if cid == 3:
            raise PermissionError("principal grant negado")
        return True

    out = _build(service, [9, 3], validate=validate)
    assert out["summary"]["companies_skipped"] == 1 and {i["company_id"] for i in out["items"]} == {9}
    assert all(c["company_ids"] != [3] for c in service.calls)


def test_no_companies_means_empty_result_without_reading(service):
    out = _build(service, [])
    assert out["items"] == [] and out["summary"]["companies_scanned"] == 0 and service.calls == []


def test_duplicates_are_scanned_once(service):
    _build(service, [9, 9, 9])
    assert len(service.calls) == 1


def test_global_limit_applies_after_merging_and_summary_stays_complete(service):
    out = _build(service, [9, 1, 3], limit=2)
    assert out["returned"] == 2 and len(out["items"]) == 2 and out["summary"]["total"] == 4


def test_companies_are_listed_by_overdue_then_total(service):
    out = _build(service, [9, 1, 3, 2])
    assert [row["company_id"] for row in out["companies"]] == [9, 1, 3, 2]


# ---- ferramenta registrada --------------------------------------------------------------------
@pytest.fixture
def tool(monkeypatch):
    server = FastMCP("probe")
    my_work.register_my_work_mcp_tools(server)
    return server._tool_manager.get_tool("list_my_work_all_companies")


def test_schema_has_no_company_or_user_parameter(tool):
    props = set(tool.parameters["properties"])
    assert props == {"due", "limit"}


def test_requires_an_authenticated_user(tool, monkeypatch):
    monkeypatch.setattr("src.intelligence.tools_support.get_active_user_id", lambda: None)
    with pytest.raises(PermissionError):
        tool.fn()


@pytest.mark.parametrize("kwargs", [{"limit": 0}, {"limit": 101}, {"limit": True}, {"due": "week"}, {"due": ""}])
def test_invalid_arguments_are_rejected_before_any_lookup(tool, monkeypatch, kwargs):
    monkeypatch.setattr("src.intelligence.tools_support.get_active_user_id", lambda: 3)
    with pytest.raises(ValueError):
        tool.fn(**kwargs)


def test_company_list_comes_from_the_server_context_and_each_one_is_validated(tool, monkeypatch, service):
    import src.core.mcp_runtime as runtime
    import models.company as company_module

    seen = []

    def fake_resolve(payload=None, **kwargs):
        seen.append((dict(payload or {}), kwargs))
        if kwargs.get("allow_missing_company"):
            return SimpleNamespace(accessible_company_ids=(9, 1), company_id=None)
        if payload["company_id"] == 1:
            raise PermissionError("grant negado")
        return SimpleNamespace(company_id=payload["company_id"])

    monkeypatch.setattr(runtime, "resolve_mcp_execution_context", fake_resolve)
    monkeypatch.setattr("src.intelligence.tools_support.get_active_user_id", lambda: 3)
    fake_query = SimpleNamespace(filter=lambda *_a, **_k: SimpleNamespace(all=lambda: [SimpleNamespace(id=9, name="AA"), SimpleNamespace(id=1, name="AL")]))
    monkeypatch.setattr(company_module, "Company", SimpleNamespace(id=SimpleNamespace(in_=lambda ids: ids), query=fake_query))
    out = tool.fn(due="open", limit=10)
    assert seen[0] == ({}, {"allow_missing_company": True})
    assert [p for p, k in seen[1:]] == [{"company_id": 1}, {"company_id": 9}]
    assert out["summary"]["companies_skipped"] == 1
    assert {i["company_id"] for i in out["items"]} == {9}
