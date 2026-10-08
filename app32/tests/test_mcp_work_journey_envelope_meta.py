"""Metadados do envelope do quadro da jornada (mcp-versus): refletem o catálogo e o contexto."""
from __future__ import annotations

from datetime import date

import pytest

import src.core.mcp_work_journey_tools as tools
from src.intelligence.mcp_contracts import WorkJourneyBoardQuery
from src.intelligence.tool_catalog import catalog
from src.intelligence.tool_context import reset_sapiens_context, set_sapiens_context


def _query(company_id=9):
    return WorkJourneyBoardQuery(company_id=company_id, employee_id=23, anchor_date=date(2026, 10, 8), scope="day")


def _envelope(company_id=9):
    return tools._build_work_journey_board_envelope({"period_items": [], "summary": {}}, _query(company_id))


def test_board_envelope_carries_company_and_catalog_permission():
    meta = _envelope(9)["meta"]
    declared = list(catalog.get_tool_capability("get_work_journey_board_tool").permissions)
    assert meta["company_id"] == 9
    assert meta["permissions"] == declared == ["work_journey.board.read"]
    assert meta["capability"] == "work_journey.board.read"
    assert meta["tenant_safe"] is True and meta["human_gate_required"] is False
    assert meta["scope"] == "mcp_user" and meta["domain"] == "work_journey"


def test_board_envelope_company_follows_the_query():
    assert _envelope(1)["meta"]["company_id"] == 1
    assert _envelope(16)["meta"]["company_id"] == 16


def test_user_id_comes_from_the_execution_context_when_present():
    token = set_sapiens_context(user_id=3, company_id=9)
    try:
        assert _envelope()["meta"]["user_id"] == 3
    finally:
        reset_sapiens_context(token)


def test_user_id_is_absent_without_context():
    token = set_sapiens_context(user_id=None, company_id=None)
    try:
        assert _envelope()["meta"]["user_id"] is None
    finally:
        reset_sapiens_context(token)


def test_unknown_tool_falls_back_to_the_previous_defaults():
    meta = tools._meta("board.read", company_id=9, tool_name="ferramenta_inexistente").model_dump()
    assert meta["permissions"] == ["work_journey.read"]
    assert meta["capability"] == "work_journey.board.read"


def test_catalog_failure_never_breaks_the_response(monkeypatch):
    import src.intelligence.tool_catalog as module

    class _Broken:
        def get_tool_capability(self, _name):
            raise RuntimeError("catalogo indisponivel")

    monkeypatch.setattr(module, "catalog", _Broken())
    meta = tools._meta("board.read", company_id=9, tool_name="get_work_journey_board_tool").model_dump()
    assert meta["permissions"] == ["work_journey.read"] and meta["company_id"] == 9


def test_error_envelope_default_is_unchanged():
    meta = tools._error_envelope(operation="block.delete", message="x")["meta"]
    assert meta["company_id"] is None and meta["permissions"] == ["work_journey.read"]


@pytest.mark.parametrize("bad", [0, -3, None])
def test_invalid_company_never_leaks_into_meta(bad):
    assert tools._meta("board.read", company_id=bad).model_dump()["company_id"] is None
