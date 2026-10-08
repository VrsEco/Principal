"""Onda 1 de `routine` no mcp-versus (SPEC classificacao_dominios_mcp_versus_v1).

14 leituras (jornada de trabalho e "meu trabalho"), publicadas atrás de MCP_VERSUS_ROUTINE_READ_ENABLED
(desligada por padrão). A flag governa listagem e registro.
"""
from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
from mcp.server.fastmcp import FastMCP

import src.core.mcp_surface_registry as registry

EXPECTED = {
    "get_work_journey_board_tool",
    "get_work_journey_capacity_report_tool",
    "get_efficiency_collaborators_analysis_tool",
    "get_process_routines_analysis_tool",
    "list_employee_process_routines_for_journey_tool",
    "list_routine_journey_bindings_tool",
    "list_work_calendar_events_tool",
    "list_work_journey_absences_tool",
    "list_work_journey_blocks_tool",
    "list_work_journey_manual_tasks_tool",
    "list_work_journey_rules_tool",
    "list_work_journey_task_inventory_tool",
    "list_work_journey_transfers_tool",
    "list_my_work_secure",
}
USER_TOKEN = SimpleNamespace(scopes=("mcp:access", "mcp:user"))


def _list_tools(monkeypatch, *, flag, permission=True, identity=USER_TOKEN):
    if flag is None:
        monkeypatch.delenv("MCP_VERSUS_ROUTINE_READ_ENABLED", raising=False)
    else:
        monkeypatch.setenv("MCP_VERSUS_ROUTINE_READ_ENABLED", flag)
    monkeypatch.setattr(registry, "_has_authenticated_mcp_permission", lambda _permission: permission)
    monkeypatch.setattr("src.core.mcp_http_auth.get_http_request_identity", lambda: identity)
    server = registry.build_oauth_unified_mcp_server()
    return server, {tool.name for tool in asyncio.run(server.list_tools())}


def test_cohort_is_exactly_the_approved_fourteen_reads():
    assert len(registry.UNIFIED_ROUTINE_READ_TOOL_NAMES) == len(set(registry.UNIFIED_ROUTINE_READ_TOOL_NAMES)) == 14
    assert set(registry.UNIFIED_ROUTINE_READ_TOOL_NAMES) == EXPECTED


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_each_tool_is_a_low_risk_tenant_scoped_read_without_gate(name):
    capability = registry.catalog.get_tool_capability(name)
    assert capability is not None, name
    assert capability.domain == "routine"
    assert getattr(capability.risk, "value", capability.risk) == "low"
    assert capability.human_gate is False
    assert "company" in tuple(capability.required_context or ())
    assert "mcp_user" in tuple(capability.scopes)
    assert name.split("_")[0] in {"get", "list"}, "onda 1 só publica leituras"


def test_mutations_and_untenanted_tools_stay_out_of_wave_one():
    out = {
        "get_work_journey_agenda_tool",  # force_regenerate: leitura que escreve
        "get_my_work", "get_tasks_today",  # legadas: empresas por conta própria, scope=team/company, texto livre
        "get_financial_bank_reconciliation_workspace",  # domínio errado
        "get_financial_budget_execution_workspace",
        "complete_task", "log_work_hours", "save_work_journey_rule_tool", "delete_work_journey_block_tool",
    }
    assert out.isdisjoint(registry.UNIFIED_ROUTINE_READ_TOOL_NAMES)


def _registered(server) -> set[str]:
    """Tools realmente registradas, sem o filtro de descoberta da política."""
    return {tool.name for tool in asyncio.run(FastMCP.list_tools(server))}


def test_flag_off_by_default_hides_and_does_not_register(monkeypatch):
    server, tools = _list_tools(monkeypatch, flag=None)
    assert EXPECTED.isdisjoint(tools)
    # Oculta mas registrada ainda seria invocável por quem conhecesse o nome.
    assert EXPECTED.isdisjoint(_registered(server))


def test_flag_on_registers_all_fourteen(monkeypatch):
    server, _ = _list_tools(monkeypatch, flag="1")
    assert EXPECTED.issubset(_registered(server))


@pytest.mark.parametrize("value", ["0", "false", "off", ""])
def test_flag_falsey_values_keep_cohort_off(monkeypatch, value):
    _, tools = _list_tools(monkeypatch, flag=value)
    assert EXPECTED.isdisjoint(tools)


@pytest.mark.parametrize("value", ["1", "true", "on"])
def test_flag_on_lists_all_fourteen_with_scope_and_permission(monkeypatch, value):
    _, tools = _list_tools(monkeypatch, flag=value)
    assert EXPECTED.issubset(tools)


def test_flag_on_still_requires_per_tool_permission(monkeypatch):
    _, tools = _list_tools(monkeypatch, flag="1", permission=False)
    assert EXPECTED.isdisjoint(tools)


def test_flag_on_still_requires_user_scope_and_baseline_access(monkeypatch):
    _, no_user = _list_tools(monkeypatch, flag="1", identity=SimpleNamespace(scopes=("mcp:access",)))
    assert EXPECTED.isdisjoint(no_user)
    _, no_access = _list_tools(monkeypatch, flag="1", identity=SimpleNamespace(scopes=("mcp:user",)))
    assert EXPECTED.isdisjoint(no_access)


def test_flag_on_does_not_change_the_other_cohorts(monkeypatch):
    _, off = _list_tools(monkeypatch, flag=None)
    _, on = _list_tools(monkeypatch, flag="1")
    assert on - off == EXPECTED
    assert off - on == set()


def test_manifest_follows_the_flag(monkeypatch):
    monkeypatch.setattr(registry, "_has_authenticated_mcp_permission", lambda _permission: True)
    monkeypatch.setattr("src.core.mcp_http_auth.get_http_request_identity", lambda: USER_TOKEN)
    monkeypatch.delenv("MCP_VERSUS_ROUTINE_READ_ENABLED", raising=False)
    off = {t["name"] for t in registry.get_unified_manifest()["tools"]}
    monkeypatch.setenv("MCP_VERSUS_ROUTINE_READ_ENABLED", "1")
    on = {t["name"] for t in registry.get_unified_manifest()["tools"]}
    assert EXPECTED.isdisjoint(off)
    assert EXPECTED.issubset(on)
