"""Contrato automático e mecanismo das coortes de leitura do mcp-versus."""
from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
from mcp.server.fastmcp import FastMCP

import src.core.mcp_read_cohorts as cohorts
import src.core.mcp_surface_registry as registry
from src.core.mcp_cohort_contract import ToolProbe, audit_read_tool, probe_registered_tools
from src.intelligence.tool_catalog import catalog

ALL_COHORT_NAMES = sorted({*registry.UNIFIED_ROUTINE_READ_TOOL_NAMES, *cohorts.all_read_cohort_names()})


@pytest.fixture(scope="module")
def probes():
    return probe_registered_tools()


# ---- contrato aplicado a todas as coortes publicadas --------------------------------------
@pytest.mark.parametrize("name", ALL_COHORT_NAMES)
def test_every_published_read_tool_passes_the_contract(name, probes):
    problems = audit_read_tool(name, capability=catalog.get_tool_capability(name), probe=probes.get(name))
    assert not problems, "\n".join(problems)


# ---- o próprio contrato detecta o que deve detectar (ferramentas sintéticas) --------------
def _cap(**over):
    base = dict(risk="low", human_gate=False, scopes=("mcp_user",), permissions=("x.read",), tags=())
    base.update(over)
    return SimpleNamespace(**base)


def _probe(params=("company_id",), source="def f():\n    return 1\n"):
    return ToolProbe(schema={"properties": {p: {} for p in params}}, source=source)


def test_clean_read_passes():
    assert audit_read_tool("list_things", capability=_cap(), probe=_probe()) == []


@pytest.mark.parametrize(
    "case,kwargs,needle",
    [
        ("sem capability", dict(capability=None, probe=_probe()), "ausente do catálogo"),
        ("nao registrada", dict(capability=_cap(), probe=None), "não está registrada"),
        ("risco medio", dict(capability=_cap(risk="medium"), probe=_probe()), "risco"),
        ("com gate", dict(capability=_cap(human_gate=True), probe=_probe()), "gate humano"),
        ("sem company", dict(capability=_cap(), probe=_probe(params=("employee_id",))), "sem company_id"),
        ("force_regenerate", dict(capability=_cap(), probe=_probe(params=("company_id", "force_regenerate"))), "parâmetro suspeito"),
        ("sem escopo alcancavel", dict(capability=_cap(scopes=("mcp_admin", "sapiens")), probe=_probe()), "sem escopo alcançável"),
        ("sem permissao", dict(capability=_cap(permissions=()), probe=_probe()), "sem permissão"),
        ("escrita no codigo", dict(capability=_cap(), probe=_probe(source="def f():\n    db.session.commit()\n")), "escrita"),
    ],
)
def test_contract_flags_each_violation(case, kwargs, needle):
    problems = audit_read_tool("list_things", **kwargs)
    assert any(needle in problem for problem in problems), (case, problems)


def test_non_read_verb_is_flagged_unless_reviewed(monkeypatch):
    assert any("verbo" in p for p in audit_read_tool("generate_report", capability=_cap(), probe=_probe()))
    monkeypatch.setitem(__import__("src.core.mcp_cohort_contract", fromlist=["x"]).REVIEWED_VERB_EXCEPTIONS, "generate_report", "revisada")
    assert audit_read_tool("generate_report", capability=_cap(), probe=_probe()) == []


def test_public_tool_without_permission_is_accepted_when_explicit():
    cap = _cap(permissions=(), tags=("no_permission_required",))
    assert audit_read_tool("get_help", capability=cap, probe=_probe()) == []


# ---- mecanismo: escopo e superfície derivados da capability -------------------------------
@pytest.mark.parametrize(
    "scopes,token,surface",
    [
        (("mcp_user", "mcp_admin"), "mcp:user", "user"),
        (("mcp_analytics", "mcp_admin"), "mcp:analytics", "analytics"),
        (("mcp_finance",), "mcp:finance", "finance"),
        (("mcp_analytics", "mcp_user"), "mcp:user", "user"),
        (("sapiens", "mcp_admin"), None, "user"),
    ],
)
def test_token_scope_and_surface_follow_the_capability(scopes, token, surface):
    cap = SimpleNamespace(scopes=scopes)
    assert cohorts.token_scope_for(cap) == token
    assert cohorts.policy_surface_for(cap) == surface


def test_env_parsing(monkeypatch):
    monkeypatch.delenv(cohorts.ENV_DOMAINS, raising=False)
    assert cohorts.enabled_read_domains() == frozenset()
    monkeypatch.setenv(cohorts.ENV_DOMAINS, " Strategy , finance,, ")
    assert cohorts.enabled_read_domains() == frozenset({"strategy", "finance"})


# ---- mecanismo ponta a ponta com uma coorte simulada (um caminho LangChain e um de registrador)
LC_TOOL = "list_plans"                     # ferramenta LangChain
REGISTRAR_TOOL = "get_strategy_identity_tool"  # via registrador


def _server(monkeypatch, env):
    monkeypatch.setitem(cohorts.READ_COHORT_TOOL_NAMES, "demo", (LC_TOOL, REGISTRAR_TOOL))
    monkeypatch.setattr(registry, "_has_authenticated_mcp_permission", lambda _p: True)
    monkeypatch.setattr(
        "src.core.mcp_http_auth.get_http_request_identity",
        lambda: SimpleNamespace(scopes=("mcp:access", "mcp:user", "mcp:analytics", "mcp:finance")),
    )
    if env is None:
        monkeypatch.delenv(cohorts.ENV_DOMAINS, raising=False)
    else:
        monkeypatch.setenv(cohorts.ENV_DOMAINS, env)
    server = registry.build_oauth_unified_mcp_server()
    listed = {t.name for t in asyncio.run(server.list_tools())}
    registered = {t.name for t in asyncio.run(FastMCP.list_tools(server))}
    return server, listed, registered


def test_domain_off_by_default_is_neither_listed_nor_registered(monkeypatch):
    _, listed, registered = _server(monkeypatch, None)
    assert not ({LC_TOOL, REGISTRAR_TOOL} & listed)
    assert not ({LC_TOOL, REGISTRAR_TOOL} & registered)


def test_other_domain_flag_does_not_enable_this_domain(monkeypatch):
    _, listed, registered = _server(monkeypatch, "outro")
    assert not ({LC_TOOL, REGISTRAR_TOOL} & (listed | registered))


def test_domain_on_lists_and_registers_both_paths_with_the_size_guard(monkeypatch):
    server, listed, registered = _server(monkeypatch, "demo")
    assert {LC_TOOL, REGISTRAR_TOOL} <= listed
    assert {LC_TOOL, REGISTRAR_TOOL} <= registered
    for name in (LC_TOOL, REGISTRAR_TOOL):
        assert getattr(server._tool_manager.get_tool(name).fn, "__app32_result_guarded__", False) is True, name


def test_domain_on_still_requires_permission_and_scope(monkeypatch):
    monkeypatch.setitem(cohorts.READ_COHORT_TOOL_NAMES, "demo", (LC_TOOL, REGISTRAR_TOOL))
    monkeypatch.setenv(cohorts.ENV_DOMAINS, "demo")
    monkeypatch.setattr(registry, "_has_authenticated_mcp_permission", lambda _p: False)
    monkeypatch.setattr("src.core.mcp_http_auth.get_http_request_identity", lambda: SimpleNamespace(scopes=("mcp:access", "mcp:user")))
    server = registry.build_oauth_unified_mcp_server()
    assert not ({LC_TOOL, REGISTRAR_TOOL} & {t.name for t in asyncio.run(server.list_tools())})
    monkeypatch.setattr(registry, "_has_authenticated_mcp_permission", lambda _p: True)
    monkeypatch.setattr("src.core.mcp_http_auth.get_http_request_identity", lambda: SimpleNamespace(scopes=("mcp:user",)))
    server = registry.build_oauth_unified_mcp_server()
    assert not ({LC_TOOL, REGISTRAR_TOOL} & {t.name for t in asyncio.run(server.list_tools())})


def test_enabling_a_domain_changes_nothing_else(monkeypatch):
    _, off, _ = _server(monkeypatch, None)
    _, on, _ = _server(monkeypatch, "demo")
    assert on - off == {LC_TOOL, REGISTRAR_TOOL}
    assert off - on == set()


def test_manifest_follows_the_domain_flag(monkeypatch):
    monkeypatch.setitem(cohorts.READ_COHORT_TOOL_NAMES, "demo", (LC_TOOL, REGISTRAR_TOOL))
    monkeypatch.setattr(registry, "_has_authenticated_mcp_permission", lambda _p: True)
    monkeypatch.setattr("src.core.mcp_http_auth.get_http_request_identity", lambda: SimpleNamespace(scopes=("mcp:access", "mcp:user", "mcp:analytics")))
    monkeypatch.delenv(cohorts.ENV_DOMAINS, raising=False)
    off = {t["name"] for t in registry.get_unified_manifest()["tools"]}
    monkeypatch.setenv(cohorts.ENV_DOMAINS, "demo")
    on = {t["name"] for t in registry.get_unified_manifest()["tools"]}
    assert not ({LC_TOOL, REGISTRAR_TOOL} & off)
    assert {LC_TOOL, REGISTRAR_TOOL} <= on
