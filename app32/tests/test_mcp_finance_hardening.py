"""Endurecimento da coorte finance: paginação, candidatos de conciliação e módulos inexistentes."""
from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace

import pytest
from flask import Flask
from mcp.server.fastmcp import FastMCP

import src.core.mcp_read_cohorts as cohorts
import src.core.mcp_financial_tools as fin
from src.core.mcp_cohort_contract import missing_imported_modules, probe_registered_tools


@pytest.fixture
def tools(monkeypatch):
    from flask import Flask

    app = Flask("probe")
    monkeypatch.setattr("src.core.mcp_flask_app.get_mcp_flask_app", lambda *a, **k: app)
    server = FastMCP("probe")
    fin.register_financial_mcp_tools(server)
    return server._tool_manager


PAGED = [
    "list_financial_schedules",
    "list_financial_borderos",
    "list_financial_import_batches",
    "list_financial_ingestion_records",
    "list_financial_classification_pending",
    "list_financial_classification_suggestions",
    "list_financial_classification_memories",
    "list_financial_domain_enablements",
]


@pytest.mark.parametrize("name", PAGED)
def test_heavy_finance_lists_expose_limit_and_offset(name):
    probes = probe_registered_tools()
    props = (probes[name].schema or {}).get("properties", {})
    assert {"limit", "offset"} <= set(props), name
    assert props["limit"].get("default") == 20


def test_paged_helper_shape():
    out = fin._paged(list(range(45)), 20, 20)
    assert out["items"] == list(range(20, 40)) and out["count"] == 45
    assert out["has_more"] is True and out["next_offset"] == 40 and out["success"] is True


def test_closings_tool_is_not_published_while_its_module_is_missing():
    assert "list_financial_closings" not in cohorts.READ_COHORT_TOOL_NAMES["finance"]
    assert len(cohorts.READ_COHORT_TOOL_NAMES["finance"]) == 24


def test_every_published_finance_tool_imports_only_existing_modules():
    probes = probe_registered_tools()
    for name in cohorts.all_read_cohort_names():
        assert not missing_imported_modules(probes[name].source), name


def test_missing_module_is_detected():
    src = "def t():\n    from services.financial_closing_service import FinancialClosingService\n"
    assert missing_imported_modules(src) == ["services.financial_closing_service"]
    assert missing_imported_modules("    from services.financial_import_service import X\n") == []
    assert missing_imported_modules("    from os import path\n") == []


def test_bank_reconciliation_candidates_returns_the_service_list(tools, monkeypatch):
    ranked = [{"score": 0.9, "reason": "valor", "entry": {"id": 1}}]
    monkeypatch.setattr(
        "services.financial_reconciliation_workspace_service.FinancialReconciliationWorkspaceService.list_row_candidates",
        staticmethod(lambda **kw: (ranked, None)),
    )
    out = tools.get_tool("list_financial_bank_reconciliation_candidates").fn(company_id=9, row_id=5)
    assert out == {"success": True, "row_id": 5, "items": ranked, "count": 1}


def test_domain_enablements_paginates_each_type(tools, monkeypatch):
    monkeypatch.setattr(
        "services.financial_domain_enablement_service.FinancialDomainEnablementService.list_items",
        staticmethod(lambda **kw: ({"items_by_type": {"project": list(range(30)), "process": [1]}}, None)),
    )
    out = tools.get_tool("list_financial_domain_enablements").fn(company_id=9, limit=10)
    assert len(out["items_by_type"]["project"]) == 10 and out["pagination_by_type"]["project"]["has_more"] is True
    assert out["pagination_by_type"]["process"]["total"] == 1


@pytest.mark.parametrize("limit,offset", [(0, 0), (101, 0), (5, -1)])
def test_invalid_pagination_is_rejected(tools, limit, offset):
    with pytest.raises(ValueError):
        tools.get_tool("list_financial_schedules").fn(company_id=9, limit=limit, offset=offset)
