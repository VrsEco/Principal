"""Comercial e financeiro no mcp-versus: o ator das escritas é o usuário da sessão (M2)."""
from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace

import pytest
from flask import Flask
from mcp.server.fastmcp import FastMCP

import src.core.mcp_commercial_tools as commercial
import src.core.mcp_financial_tools as financial
from src.core.mcp_cohort_contract import probe_registered_tools

ACTOR_TOOLS = [
    "create_commercial_contract",
    "update_commercial_contract_general",
    "suspend_commercial_contract",
    "close_commercial_contract",
    "delete_commercial_contract",
    "upsert_commercial_contract_financial_terms",
    "upsert_commercial_contract_fiscal_terms",
    "generate_commercial_billing_batch",
    "generate_commercial_financial_titles_for_billing",
    "cancel_commercial_billing",
    "update_commercial_fiscal_entry",
    "assign_commercial_fiscal_batch",
    "remove_commercial_fiscal_batch",
    "update_commercial_fiscal_status",
    "export_commercial_fiscal_integration_spreadsheet",
    "review_financial_ingestion_record",
]
IDENTITY = {"user_id", "reviewed_by_user_id", "reviewer_user_id", "approver_user_id", "actor_user_id"}


@pytest.fixture(scope="module")
def probes():
    return probe_registered_tools()


@pytest.mark.parametrize("name", ACTOR_TOOLS)
def test_no_commercial_or_financial_write_accepts_identity_from_the_client(probes, name):
    props = set((probes[name].schema or {}).get("properties", {}))
    assert props.isdisjoint(IDENTITY), f"{name}: {props & IDENTITY}"
    assert "company_id" in props


@pytest.fixture
def commercial_tools(monkeypatch):
    app = Flask("probe")
    monkeypatch.setattr("src.core.mcp_flask_app.get_mcp_flask_app", lambda *a, **k: app)
    server = FastMCP("probe")
    commercial.register_commercial_mcp_tools(server)
    return server._tool_manager


def _session(monkeypatch, user_id):
    monkeypatch.setattr(commercial, "get_http_request_context", lambda: {"user_id": user_id} if user_id else {})


def test_contract_creation_is_attributed_to_the_session_user(commercial_tools, monkeypatch):
    seen = {}
    _session(monkeypatch, 55)

    class _Contract:
        def to_dict(self):
            return {"id": 1}

    def fake_create(**kw):
        seen.update(kw)
        return _Contract()

    monkeypatch.setattr("services.contracts_service.ContractService.create_contract", staticmethod(fake_create))
    out = commercial_tools.get_tool("create_commercial_contract").fn(company_id=9, payload={"title": "x"})
    assert out["success"] is True and seen["user_id"] == 55 and seen["company_id"] == 9


def test_billing_cancellation_is_attributed_to_the_session_user(commercial_tools, monkeypatch):
    seen = {}
    _session(monkeypatch, 56)

    class _Billing:
        def to_dict(self):
            return {"id": 3}

    def fake_cancel(**kw):
        seen.update(kw)
        return _Billing()

    monkeypatch.setattr("services.contracts_service.ContractService.cancel_native_billing", staticmethod(fake_cancel))
    out = commercial_tools.get_tool("cancel_commercial_billing").fn(company_id=9, billing_id=3, reason="r")
    assert out["success"] is True and seen["user_id"] == 56


@pytest.mark.parametrize(
    "name,kwargs",
    [
        ("create_commercial_contract", {"payload": {}}),
        ("cancel_commercial_billing", {"billing_id": 1}),
        ("delete_commercial_contract", {"contract_id": 1}),
    ],
)
def test_writes_without_a_session_user_are_refused_before_any_service_call(commercial_tools, monkeypatch, name, kwargs):
    _session(monkeypatch, None)
    called = []
    monkeypatch.setattr("services.contracts_service.ContractService.create_contract", staticmethod(lambda **kw: called.append(kw)))
    monkeypatch.setattr("services.contracts_service.ContractService.cancel_native_billing", staticmethod(lambda **kw: called.append(kw)))
    monkeypatch.setattr("services.contracts_service.ContractService.get_contract", staticmethod(lambda *a, **k: called.append(a)))
    with pytest.raises(PermissionError):
        commercial_tools.get_tool(name).fn(company_id=9, **kwargs)
    assert called == []


def test_ingestion_review_uses_the_session_user_as_reviewer(monkeypatch):
    app = Flask("probe")
    monkeypatch.setattr("src.core.mcp_flask_app.get_mcp_flask_app", lambda *a, **k: app)
    monkeypatch.setattr("src.core.mcp_session_actor.get_http_request_context", lambda: {"user_id": 57})
    seen = {}
    monkeypatch.setattr(
        "services.financial_ingestion_service.FinancialIngestionService.review_record",
        staticmethod(lambda **kw: (seen.update(kw) or {"id": 1}, None)),
    )
    server = FastMCP("probe")
    financial.register_financial_mcp_tools(server)
    out = server._tool_manager.get_tool("review_financial_ingestion_record").fn(company_id=9, record_id=1, review_status="approved")
    assert out["success"] is True and seen["reviewed_by_user_id"] == 57


def test_ingestion_review_without_a_session_user_is_refused(monkeypatch):
    monkeypatch.setattr("src.core.mcp_session_actor.get_http_request_context", lambda: {})
    server = FastMCP("probe")
    financial.register_financial_mcp_tools(server)
    with pytest.raises(PermissionError):
        server._tool_manager.get_tool("review_financial_ingestion_record").fn(company_id=9, record_id=1, review_status="approved")
