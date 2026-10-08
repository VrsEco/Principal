"""Leituras comerciais do mcp-versus: paginação das listas pesadas e sem texto livre (notes)."""
from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace

import pytest
from mcp.server.fastmcp import FastMCP

import src.core.mcp_commercial_tools as commercial


class _Record:
    def __init__(self, **data):
        self._data = data

    def to_dict(self):
        return dict(self._data)


def _rows(n):
    return [
        {
            "billing": _Record(id=i, notes="obs livre do faturamento"),
            "contract": _Record(id=100 + i, notes="obs do contrato"),
            "party": _Record(id=200 + i, name=f"Cliente {i}", notes="e-mail pessoal do gestor"),
            "retention_amount": 1,
            "item_count": 1,
        }
        for i in range(n)
    ]


@pytest.fixture
def tools(monkeypatch):
    @contextmanager
    def _ctx():
        yield

    fake_app = SimpleNamespace(app_context=_ctx)
    monkeypatch.setattr("app.create_app", lambda: fake_app)
    server = FastMCP("probe")
    commercial.register_commercial_mcp_tools(server)
    return server._tool_manager


@pytest.fixture
def services(monkeypatch):
    rows = _rows(45)
    monkeypatch.setattr("services.contracts_service.ContractService.list_native_billings_done", staticmethod(lambda cid, f: rows))
    monkeypatch.setattr(
        "services.contracts_service.ContractService.list_fiscal_invoice_workspace",
        staticmethod(lambda cid, f: {"rows": rows, "batches": [], "kpis": {}, "status_counts": {}}),
    )
    return rows


@pytest.mark.parametrize("limit,offset", [(0, 0), (101, 0), (True, 0), ("5", 0), (5, -1), (5, None)])
def test_invalid_pagination_is_rejected(limit, offset):
    with pytest.raises(ValueError):
        commercial.validated_page(limit, offset)


def test_page_window_and_cursor():
    window = commercial.page_of(list(range(45)), 20, 40)
    assert window["window"] == [40, 41, 42, 43, 44]
    assert window["total"] == 45 and window["returned"] == 5 and window["has_more"] is False and window["next_offset"] is None
    first = commercial.page_of(list(range(45)), 20, 0)
    assert first["has_more"] is True and first["next_offset"] == 20


@pytest.mark.parametrize("name,key", [("list_commercial_billings_done", "items"), ("list_commercial_fiscal_workspace", "rows")])
def test_heavy_lists_are_paginated_without_free_text(tools, services, name, key):
    tool = tools.get_tool(name)
    assert {"limit", "offset"} <= set(tool.parameters["properties"])
    first = tool.fn(company_id=9)
    assert first["success"] is True and first["total"] == 45 and first["returned"] == 20 and first["next_offset"] == 20
    assert len(first[key]) == 20
    last = tool.fn(company_id=9, limit=20, offset=40)
    assert last["returned"] == 5 and last["has_more"] is False
    for row in first[key]:
        for section in ("billing", "contract", "party"):
            assert "notes" not in row[section], f"{section}.notes vazou em {name}"


def test_customers_listing_drops_notes(tools, monkeypatch):
    monkeypatch.setattr(
        "services.financial_catalog_service.FinancialCatalogService.list_items",
        staticmethod(lambda **kw: ([{"id": 1, "name": "A", "is_customer": True, "notes": "texto livre", "document_number": "1"}], None)),
    )
    out = tools.get_tool("list_commercial_customers").fn(company_id=9)
    assert out["count"] == 1 and "notes" not in out["items"][0] and out["items"][0]["name"] == "A"
