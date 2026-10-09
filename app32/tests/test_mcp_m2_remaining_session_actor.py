"""Últimas três ferramentas com identidade vinda do cliente (M2): agora o ator é a sessão."""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from mcp.server.fastmcp import FastMCP

import src.core.mcp_incentive_tools as incentive
import src.core.mcp_integration_request_tools as integration
import src.core.mcp_self_service_tools as self_service
from src.core.mcp_cohort_contract import probe_registered_tools
from src.intelligence.tool_catalog import catalog

IDENTITY = {"user_id", "requester_user_id", "requester_name", "request_id", "trace_id", "actor_user_id"}


@pytest.fixture(scope="module")
def probes():
    return probe_registered_tools()


@pytest.mark.parametrize(
    "name", ["generate_strategic_connection_summary", "request_new_app32_integration", "update_my_contacts_secure"]
)
def test_schema_has_no_identity_parameter_and_has_company_id(probes, name):
    props = set((probes[name].schema or {}).get("properties", {}))
    assert props.isdisjoint(IDENTITY), f"{name}: {props & IDENTITY}"
    assert "company_id" in props


def test_update_my_contacts_is_a_known_self_service_capability():
    capability = catalog.get_tool_capability("update_my_contacts_secure")
    assert capability.domain == "identity_self_service" and tuple(capability.permissions) == ("user.contacts.update",)
    assert set(capability.required_context) == {"user", "company"}


@pytest.fixture
def contacts(monkeypatch):
    user = SimpleNamespace(whatsapp="old", telegram="old")
    seen = {"commit": 0, "looked_up": None}

    class _Query:
        def get(self, user_id):
            seen["looked_up"] = user_id
            return user

    monkeypatch.setattr("models.user.User", SimpleNamespace(query=_Query()))
    monkeypatch.setattr("models.db", SimpleNamespace(session=SimpleNamespace(commit=lambda: seen.update(commit=seen["commit"] + 1))))
    monkeypatch.setattr("src.core.mcp_session_actor.get_http_request_context", lambda: {"user_id": 61})
    server = FastMCP("probe")
    self_service.register_self_service_mcp_tools(server)
    return SimpleNamespace(tool=server._tool_manager.get_tool("update_my_contacts_secure"), user=user, seen=seen)


def test_contacts_are_updated_only_for_the_session_user(contacts):
    out = contacts.tool.fn(company_id=9, whatsapp=" +5571999990000 ")
    assert out == {"updated": ["whatsapp"]}
    assert contacts.seen["looked_up"] == 61 and contacts.seen["commit"] == 1
    assert contacts.user.whatsapp == "+5571999990000" and contacts.user.telegram == "old"


@pytest.mark.parametrize("kwargs", [{}, {"whatsapp": "x" * 65}])
def test_contacts_validation(contacts, kwargs):
    with pytest.raises(ValueError):
        contacts.tool.fn(company_id=9, **kwargs)
    assert contacts.seen["commit"] == 0


def test_contacts_without_a_session_user_are_refused(contacts, monkeypatch):
    monkeypatch.setattr("src.core.mcp_session_actor.get_http_request_context", lambda: {})
    with pytest.raises(PermissionError):
        contacts.tool.fn(company_id=9, whatsapp="1")
    assert contacts.seen["looked_up"] is None


def test_integration_request_without_a_session_user_is_refused(monkeypatch):
    monkeypatch.setattr("src.core.mcp_session_actor.get_http_request_context", lambda: {})
    server = FastMCP("probe")
    integration.register_integration_request_tools(server)
    tool = server._tool_manager.get_tool("request_new_app32_integration")
    called = []
    monkeypatch.setattr(integration.IntegrationRequestService, "create_request", lambda *a, **k: called.append(1))
    with pytest.raises(PermissionError):
        tool.fn(
            company_id=9, title="t", business_domain="d", integration_mode="consume", technical_channel="api_mcp",
            external_system="x", objective="o" * 20, data_summary="d",
        )
    assert called == []


def test_connection_summary_meta_carries_the_session_user(monkeypatch):
    monkeypatch.setattr("src.core.mcp_session_actor.get_http_request_context", lambda: {"user_id": 62})
    monkeypatch.setattr("src.intelligence.tools_support.get_active_user_id", lambda: 62)
    monkeypatch.setattr(incentive, "_build_connection_graph_payload", lambda **k: {"graph": {"nodes": [], "links": [], "summary": {}}, "snapshot": {}, "limitations": []})
    monkeypatch.setattr(incentive, "_calculate_connection_metrics", lambda graph: {"total_nodes": 0, "total_links": 0, "by_health": {}})
    monkeypatch.setattr(incentive, "_build_connection_findings", lambda metrics: [])
    server = FastMCP("probe")
    incentive.register_incentive_tools(server)
    out = server._tool_manager.get_tool("generate_strategic_connection_summary").fn(company_id=9)
    assert out["meta"]["user_id"] == 62
