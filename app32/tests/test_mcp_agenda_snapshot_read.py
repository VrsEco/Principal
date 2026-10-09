"""get_work_journey_agenda_snapshot_tool: lê a agenda já gerada, sem reconstruir nem gravar."""
from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pytest

import services.work_journey_agenda_service as svc
from src.core.mcp_cohort_contract import audit_read_tool, probe_registered_tools
from src.intelligence.tool_catalog import catalog

ANCHOR = date(2026, 10, 8)


@pytest.fixture
def guard(monkeypatch):
    """Falha o teste se a leitura tentar construir, sincronizar ou gravar."""

    def boom(*a, **k):
        raise AssertionError("a leitura não pode reconstruir nem gravar a agenda")

    monkeypatch.setattr(svc, "_build_agenda_snapshot", boom)
    monkeypatch.setattr(svc, "_get_or_build_agenda", boom)
    monkeypatch.setattr(svc, "sync_work_journey_items", boom)
    monkeypatch.setattr(svc, "db", SimpleNamespace(session=SimpleNamespace(commit=boom, add=boom, flush=boom, delete=boom)))
    monkeypatch.setattr(svc, "ensure_employee", lambda company_id, employee_id: SimpleNamespace(id=employee_id))


def _query_returning(monkeypatch, agenda):
    captured = {}

    class Q:
        def filter_by(self, **kw):
            captured.update(kw)
            return self

        def first(self):
            return agenda

    monkeypatch.setattr(svc, "WorkJourneyAgenda", SimpleNamespace(query=Q()))
    return captured


def test_missing_agenda_is_reported_not_created(monkeypatch, guard):
    captured = _query_returning(monkeypatch, None)
    out = svc.read_work_journey_agenda(9, 23, ANCHOR, "week")
    assert out["generated"] is False and out["agenda"] is None and "hint" in out
    assert captured == {"company_id": 9, "employee_id": 23, "anchor_date": ANCHOR, "scope": "week"}


def test_existing_agenda_is_serialized_as_is(monkeypatch, guard):
    agenda = SimpleNamespace(id=5)
    _query_returning(monkeypatch, agenda)
    monkeypatch.setattr(svc, "_serialize", lambda a, e: {"agenda_id": a.id, "employee_id": e.id})
    out = svc.read_work_journey_agenda(9, 23, ANCHOR, "day")
    assert out == {"generated": True, "agenda": {"agenda_id": 5, "employee_id": 23}}


def test_unknown_scope_falls_back_to_week(monkeypatch, guard):
    captured = _query_returning(monkeypatch, None)
    svc.read_work_journey_agenda(9, 23, ANCHOR, "year")
    assert captured["scope"] == "week"


def test_tool_has_no_regeneration_parameter_and_passes_the_contract():
    probes = probe_registered_tools()
    name = "get_work_journey_agenda_snapshot_tool"
    props = set((probes[name].schema or {}).get("properties", {}))
    assert props == {"company_id", "employee_id", "anchor_date", "scope"}
    assert audit_read_tool(name, capability=catalog.get_tool_capability(name), probe=probes[name]) == []


def test_the_old_regenerating_tool_stays_out_of_the_cohort():
    import src.core.mcp_surface_registry as registry

    assert "get_work_journey_agenda_tool" not in registry.UNIFIED_ROUTINE_READ_TOOL_NAMES
    assert "get_work_journey_agenda_snapshot_tool" in registry.UNIFIED_ROUTINE_READ_TOOL_NAMES
