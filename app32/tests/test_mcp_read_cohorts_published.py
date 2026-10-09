"""Coortes de leitura por assunto publicadas no mcp-versus (60 ferramentas)."""
from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
from mcp.server.fastmcp import FastMCP

import src.core.mcp_read_cohorts as cohorts
import src.core.mcp_surface_registry as registry
from src.intelligence.tool_catalog import catalog

EXPECTED_COUNTS = {"strategy": 13, "processes": 4, "platform": 3, "knowledge": 2, "commercial": 14, "finance": 24}
ALL_SUBJECTS = ",".join(EXPECTED_COUNTS)
IDENTITY = SimpleNamespace(scopes=("mcp:access", "mcp:user", "mcp:analytics", "mcp:finance"))


def _build(monkeypatch, env, *, permission=True, identity=IDENTITY):
    if env is None:
        monkeypatch.delenv(cohorts.ENV_DOMAINS, raising=False)
    else:
        monkeypatch.setenv(cohorts.ENV_DOMAINS, env)
    monkeypatch.setenv("MCP_VERSUS_ROUTINE_READ_ENABLED", "0")
    monkeypatch.setattr(registry, "_has_authenticated_mcp_permission", lambda _p: permission)
    monkeypatch.setattr("src.core.mcp_http_auth.get_http_request_identity", lambda: identity)
    server = registry.build_oauth_unified_mcp_server()
    listed = {t.name for t in asyncio.run(server.list_tools())}
    registered = {t.name for t in asyncio.run(FastMCP.list_tools(server))}
    return server, listed, registered


def test_subjects_and_sizes_are_exactly_the_approved_ones():
    assert {k: len(v) for k, v in cohorts.READ_COHORT_TOOL_NAMES.items()} == EXPECTED_COUNTS
    assert len(cohorts.all_read_cohort_names()) == 60


def test_no_tool_is_in_two_cohorts_or_already_published():
    names = cohorts.all_read_cohort_names()
    assert len(names) == len(set(names))
    already = {
        n
        for attr in dir(registry)
        if (attr.startswith(("PILOT_", "UNIFIED_")) or attr == "STATUS_TOOL_NAMES") and attr.endswith("TOOL_NAMES")
        for n in getattr(registry, attr)
    }
    assert not (set(names) & already)


def test_legacy_company_blind_tools_stay_out():
    out = {"get_my_work", "get_tasks_today", "search_organizational_knowledge", "list_team_workload",
           "get_work_journey_agenda_tool", "get_project_task_analytics_report"}
    assert out.isdisjoint(cohorts.all_read_cohort_names())


def test_sensitive_subjects_have_their_own_keys():
    names = cohorts.READ_COHORT_TOOL_NAMES
    assert all("commercial" in n for n in names["commercial"])
    assert not any("financial" in n for n in names["strategy"] + names["processes"] + names["platform"] + names["commercial"])
    assert not any("commercial" in n for n in names["strategy"] + names["finance"])


@pytest.mark.parametrize("subject", sorted(EXPECTED_COUNTS))
def test_each_subject_is_off_with_none_and_only_its_own_flag_enables_it(monkeypatch, subject):
    mine = set(cohorts.READ_COHORT_TOOL_NAMES[subject])
    others = set(cohorts.all_read_cohort_names()) - mine
    _, listed, registered = _build(monkeypatch, "none")
    assert not (mine & (listed | registered))
    _, listed, registered = _build(monkeypatch, subject)
    assert mine <= listed and mine <= registered
    assert not (others & (listed | registered)), "ligar um assunto não pode expor outro"


def test_all_subjects_on_lists_all_60(monkeypatch):
    _, off, _ = _build(monkeypatch, "none")
    _, on, registered = _build(monkeypatch, ALL_SUBJECTS)
    assert on - off == set(cohorts.all_read_cohort_names())
    assert off - on == set()
    assert set(cohorts.all_read_cohort_names()) <= registered


def test_every_enabled_tool_is_registered_with_the_size_guard(monkeypatch):
    server, _, _ = _build(monkeypatch, ALL_SUBJECTS)
    manager = server._tool_manager
    missing = [n for n in cohorts.all_read_cohort_names() if getattr(manager.get_tool(n).fn, "__app32_result_guarded__", False) is not True]
    assert not missing, missing


def test_permission_and_scope_are_still_required(monkeypatch):
    _, denied, _ = _build(monkeypatch, ALL_SUBJECTS, permission=False)
    assert set(cohorts.all_read_cohort_names()).isdisjoint(denied)
    _, no_access, _ = _build(monkeypatch, "strategy", identity=SimpleNamespace(scopes=("mcp:user",)))
    assert set(cohorts.READ_COHORT_TOOL_NAMES["strategy"]).isdisjoint(no_access)


def test_each_tool_is_visible_only_with_its_own_token_scope(monkeypatch):
    user_only = SimpleNamespace(scopes=("mcp:access", "mcp:user"))
    _, listed, _ = _build(monkeypatch, ALL_SUBJECTS, identity=user_only)
    for name in cohorts.all_read_cohort_names():
        scope = cohorts.token_scope_for(catalog.get_tool_capability(name))
        assert (name in listed) == (scope == "mcp:user"), (name, scope)


DEFAULT_ON = {"strategy", "processes", "platform", "knowledge"}


def test_unset_variable_enables_exactly_the_non_sensitive_subjects(monkeypatch):
    _, off, _ = _build(monkeypatch, "none")
    _, default, registered = _build(monkeypatch, None)
    expected = {n for s in DEFAULT_ON for n in cohorts.READ_COHORT_TOOL_NAMES[s]}
    assert default - off == expected and len(expected) == 22
    sensitive = {n for s in ("commercial", "finance") for n in cohorts.READ_COHORT_TOOL_NAMES[s]}
    assert not (sensitive & (default | registered)), "comercial e financeiro nunca vêm ligados por padrão"


def test_none_is_the_emergency_switch(monkeypatch):
    _, listed, registered = _build(monkeypatch, "none")
    assert not (set(cohorts.all_read_cohort_names()) & (listed | registered))


def test_explicit_list_overrides_the_defaults(monkeypatch):
    _, listed, _ = _build(monkeypatch, "finance")
    assert set(cohorts.READ_COHORT_TOOL_NAMES["finance"]) <= listed
    assert not (set(cohorts.READ_COHORT_TOOL_NAMES["strategy"]) & listed)
