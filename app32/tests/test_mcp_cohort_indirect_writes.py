"""Escrita INDIRETA em leituras do mcp-versus: a tool chama um serviço que grava."""
from __future__ import annotations

import pytest

import src.core.mcp_cohort_contract as contract
import src.core.mcp_read_cohorts as cohorts
import src.core.mcp_surface_registry as registry
from src.core.mcp_cohort_contract import ToolProbe, audit_read_tool, indirect_write_hits, probe_registered_tools
from src.intelligence.tool_catalog import catalog

PREFIX = (__name__.split(".")[0], "tests")


# ---- cadeia sintética: tool -> servico_a -> servico_b (grava) -----------------------------
class _Session:
    def commit(self):
        return None


db = SimpleSession = _Session()


def writer_service():
    db.session = db
    db.session.commit()


def middle_service():
    return writer_service()


def pure_service():
    return 1


def tool_direct_writer():
    return writer_service()


def tool_via_argument():
    def run(callback):
        return callback()

    return run(writer_service)


def tool_two_levels():
    return middle_service()


def tool_pure():
    return pure_service()


def test_detects_a_direct_service_that_writes():
    assert any("writer_service" in h for h in indirect_write_hits(tool_direct_writer, prefixes=PREFIX))


def test_detects_a_service_passed_as_an_argument():
    assert any("writer_service" in h for h in indirect_write_hits(tool_via_argument, prefixes=PREFIX))


def test_detects_a_write_two_levels_down_but_not_three():
    assert any("writer_service" in h for h in indirect_write_hits(tool_two_levels, depth=2, prefixes=PREFIX))
    assert not any("writer_service" in h for h in indirect_write_hits(tool_two_levels, depth=1, prefixes=PREFIX))


def test_pure_chain_has_no_hits():
    assert indirect_write_hits(tool_pure, prefixes=PREFIX) == []


def test_audit_flags_an_unreviewed_indirect_write(monkeypatch):
    monkeypatch.setattr(contract, "_SERVICE_PREFIXES", PREFIX)
    from types import SimpleNamespace

    cap = SimpleNamespace(risk="low", human_gate=False, scopes=("mcp_user",), permissions=("x.read",), tags=())
    probe = ToolProbe(schema={"properties": {"company_id": {}}}, source="def f():\n    return 1\n", fn=tool_direct_writer)
    problems = audit_read_tool("list_things", capability=cap, probe=probe)
    assert any("escrita indireta" in p for p in problems)
    monkeypatch.setitem(contract.REVIEWED_INDIRECT_WRITE_EXCEPTIONS, "list_things", {"tests.writer_service": "x"})
    # o nome do hit usa o último segmento do módulo
    hit = indirect_write_hits(tool_direct_writer, prefixes=PREFIX)[0]
    monkeypatch.setitem(contract.REVIEWED_INDIRECT_WRITE_EXCEPTIONS, "list_things", {hit: "revisado"})
    assert audit_read_tool("list_things", capability=cap, probe=probe) == []


# ---- o que está publicado ---------------------------------------------------------------------
def test_reviewed_exceptions_are_exactly_the_two_known_tools_and_are_justified():
    ex = contract.REVIEWED_INDIRECT_WRITE_EXCEPTIONS
    assert set(ex) == {"list_work_journey_task_inventory_tool", "get_work_journey_board_tool"}
    for tool, callees in ex.items():
        assert callees and all(len(reason) > 40 for reason in callees.values()), tool


def test_every_exception_is_still_needed():
    """Exceção sem uso é dívida escondida: se o serviço deixar de gravar, remova a linha."""
    probes = probe_registered_tools()
    for tool, allowed in contract.REVIEWED_INDIRECT_WRITE_EXCEPTIONS.items():
        hits = set(indirect_write_hits(probes[tool].fn))
        assert hits & set(allowed), f"{tool}: exceções não correspondem a nenhuma escrita atual ({hits})"


def test_no_other_published_read_tool_writes_indirectly():
    probes = probe_registered_tools()
    names = {*registry.UNIFIED_ROUTINE_READ_TOOL_NAMES, *cohorts.all_read_cohort_names()}
    offenders = {}
    for name in sorted(names):
        extra = set(indirect_write_hits(probes[name].fn)) - set(contract.REVIEWED_INDIRECT_WRITE_EXCEPTIONS.get(name, {}))
        if extra:
            offenders[name] = sorted(extra)
    assert not offenders, offenders
