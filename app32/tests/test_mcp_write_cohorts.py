"""Coortes de ESCRITA do mcp-versus (sub-onda 2A): desligadas por padrão, por assunto, com o contrato como porta."""
from __future__ import annotations

import asyncio
import inspect
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from mcp.server.fastmcp import FastMCP

import src.core.mcp_surface_registry as registry
import src.core.mcp_write_cohorts as cohorts
from src.core.mcp_cohort_contract import probe_registered_tools
from src.core.mcp_gate_policy import requires_persisted_approval
from src.core.mcp_mutation_contract import audit_mutation_tool
from src.intelligence.tool_catalog import catalog

BASELINE = Path(__file__).parent / "data" / "mcp_mutation_violations_baseline.json"
USER = SimpleNamespace(scopes=("mcp:access", "mcp:user"))
EXPECTED = {
    "projects": {"create_project", "update_project", "update_project_task_secure"},
    "operations": {"request_engineering_suggestion", "request_new_app32_integration"},
    "meetings": {"log_meeting_discussion"},
}
ALL = set().union(*EXPECTED.values())


def _server(monkeypatch, env):
    if env is None:
        monkeypatch.delenv("MCP_VERSUS_WRITE_DOMAINS", raising=False)
    else:
        monkeypatch.setenv("MCP_VERSUS_WRITE_DOMAINS", env)
    monkeypatch.setattr(registry, "_has_authenticated_mcp_permission", lambda _p: True)
    monkeypatch.setattr("src.core.mcp_http_auth.get_http_request_identity", lambda: USER)
    server = registry.build_oauth_unified_mcp_server()
    listed = {tool.name for tool in asyncio.run(server.list_tools())}
    registered = {tool.name for tool in asyncio.run(FastMCP.list_tools(server))}
    return server, listed, registered


def test_cohort_content_is_exactly_the_approved_six():
    assert {k: set(v) for k, v in cohorts.WRITE_COHORT_TOOL_NAMES.items()} == EXPECTED
    assert len(cohorts.all_write_cohort_names()) == len(ALL) == 6


@pytest.mark.parametrize("value", [None, "", "none", "NONE", "  "])
def test_off_by_default_and_by_none(monkeypatch, value):
    _, listed, registered = _server(monkeypatch, value)
    assert ALL.isdisjoint(listed) and ALL.isdisjoint(registered), "desligada: não listar nem registrar"


@pytest.mark.parametrize("subject", sorted(EXPECTED))
def test_each_subject_turns_on_alone(monkeypatch, subject):
    _, listed, registered = _server(monkeypatch, subject)
    assert EXPECTED[subject] <= listed and EXPECTED[subject] <= registered
    other = ALL - EXPECTED[subject]
    assert other.isdisjoint(listed) and other.isdisjoint(registered)


def test_all_subjects_on_lists_all_six_and_changes_nothing_else(monkeypatch):
    _, off, _ = _server(monkeypatch, None)
    _, on, _ = _server(monkeypatch, "projects,operations,meetings")
    assert on - off == ALL and off - on == set()


def test_still_requires_user_scope_and_per_tool_permission(monkeypatch):
    monkeypatch.setenv("MCP_VERSUS_WRITE_DOMAINS", "projects,operations,meetings")
    monkeypatch.setattr("src.core.mcp_http_auth.get_http_request_identity", lambda: SimpleNamespace(scopes=("mcp:access",)))
    monkeypatch.setattr(registry, "_has_authenticated_mcp_permission", lambda _p: True)
    server = registry.build_oauth_unified_mcp_server()
    assert ALL.isdisjoint({t.name for t in asyncio.run(server.list_tools())})
    monkeypatch.setattr("src.core.mcp_http_auth.get_http_request_identity", lambda: USER)
    monkeypatch.setattr(registry, "_has_authenticated_mcp_permission", lambda _p: False)
    server = registry.build_oauth_unified_mcp_server()
    assert ALL.isdisjoint({t.name for t in asyncio.run(server.list_tools())})


def test_manifest_follows_the_flag_and_reports_the_enforced_gate(monkeypatch):
    monkeypatch.setattr(registry, "_has_authenticated_mcp_permission", lambda _p: True)
    monkeypatch.setattr("src.core.mcp_http_auth.get_http_request_identity", lambda: USER)
    monkeypatch.delenv("MCP_VERSUS_WRITE_DOMAINS", raising=False)
    off = {t["name"] for t in registry.get_unified_manifest()["tools"]}
    monkeypatch.setenv("MCP_VERSUS_WRITE_DOMAINS", "projects,operations,meetings")
    manifest = registry.get_unified_manifest()
    on = {t["name"]: t for t in manifest["tools"]}
    assert ALL.isdisjoint(off) and ALL <= set(on)
    assert all(on[name].get("human_gate") is False for name in ALL), "criar e editar não exigem aprovação (D6)"


# ---- o contrato de mutações é a porta de entrada ------------------------------------------------
def test_every_cohort_tool_passes_the_mutation_contract_and_is_not_in_the_baseline():
    probes = probe_registered_tools()
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    for name in sorted(ALL):
        problems = audit_mutation_tool(name, capability=catalog.get_tool_capability(name), probe=probes.get(name))
        assert not problems, f"{name}: {[(v.code, v.detail) for v in problems]}"
        assert name not in baseline, f"{name} está na linha de base de violações"


def test_no_cohort_tool_needs_approval_under_d6():
    for name in sorted(ALL):
        assert requires_persisted_approval(name, catalog.get_tool_capability(name)) is False, name


# ---- parâmetro do cliente oculto só no MCP ------------------------------------------------------
def test_requester_name_is_hidden_in_mcp_but_kept_for_the_chat(monkeypatch):
    server, _, _ = _server(monkeypatch, "operations")
    mcp_params = set(server._tool_manager.get_tool("request_engineering_suggestion").parameters["properties"])
    assert "requester_name" not in mcp_params and "company_id" in mcp_params

    chat_tool = next(t for t in catalog.get_langchain_tools() if t.name == "request_engineering_suggestion")
    assert "requester_name" in inspect.signature(chat_tool.func).parameters, "o chat segue com a assinatura original"


def test_hidden_parameter_adapter_injects_the_fixed_value_and_drops_the_schema_entry():
    from src.core.mcp_param_hiding import HIDDEN_CLIENT_PARAMETERS, adapt_for_mcp

    seen = {}

    def original(title: str, requester_name: str = "x", company_id: int = 0):
        seen.update(title=title, requester_name=requester_name, company_id=company_id)

    HIDDEN_CLIENT_PARAMETERS["__probe__"] = {"requester_name": None}
    try:
        adapted = adapt_for_mcp("__probe__", original)
        assert list(inspect.signature(adapted).parameters) == ["title", "company_id"]
        adapted(title="t", company_id=3)
        assert seen == {"title": "t", "requester_name": None, "company_id": 3}
    finally:
        HIDDEN_CLIENT_PARAMETERS.pop("__probe__", None)
    assert adapt_for_mcp("outra", original) is original
