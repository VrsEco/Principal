import pytest
from starlette.applications import Starlette
from starlette.testclient import TestClient

import src.core.mcp_http_server as http_server
from src.core.mcp_admin_cohort import ADMIN_CONNECTOR_TOOL_NAMES
from src.core.mcp_gate_policy import requires_persisted_approval
from src.intelligence.tool_catalog import catalog

FORBIDDEN = {
    "get_database_schema", "get_system_health", "register_system_user", "update_company_status",
    "request_agent_deployment", "approve_agent_deployment", "escalate_technical_issue",
    "publish_approved_process_modeling_package_tool", "configure_whatsapp_status_account",
}


def test_cohort_is_exactly_the_reviewed_eight_and_excludes_platform_tools():
    assert len(ADMIN_CONNECTOR_TOOL_NAMES) == len(set(ADMIN_CONNECTOR_TOOL_NAMES)) == 8
    assert not FORBIDDEN & set(ADMIN_CONNECTOR_TOOL_NAMES)
    assert all(name.startswith(("delete_", "approve_")) for name in ADMIN_CONNECTOR_TOOL_NAMES)


@pytest.mark.parametrize("name", ADMIN_CONNECTOR_TOOL_NAMES)
def test_each_tool_is_admin_scoped_and_requires_persisted_approval(name):
    capability = catalog.get_tool_capability(name)
    assert capability is not None
    scopes = {getattr(scope, "value", scope) for scope in capability.scopes}
    assert "mcp_admin" in scopes
    assert not scopes & {"mcp_user", "mcp_analytics", "mcp_finance"}, "nunca aparece no conector comum"
    assert requires_persisted_approval(name, capability) is True


def test_connector_lists_only_the_cohort_plus_discovery_and_no_diagnostics():
    from src.core.mcp_surface_registry import build_oauth_admin_mcp_server

    names = {tool.name for tool in build_oauth_admin_mcp_server()._tool_manager.list_tools()}
    assert names == set(ADMIN_CONNECTOR_TOOL_NAMES) | {"list_admin_app32_capabilities"}


def test_route_is_opt_in_and_publishes_the_admin_scope(monkeypatch):
    monkeypatch.setattr(http_server, "build_surface_http_app", lambda surface, **kw: Starlette())
    monkeypatch.delenv("APP32_MCP_OIDC_ADMIN_ROUTE_ENABLED", raising=False)
    off = {getattr(route, "path", None) for route in http_server.create_http_app().routes}
    assert "/mcp/pilot/admin" not in off
    assert "/.well-known/oauth-protected-resource/mcp/pilot/admin" not in off

    monkeypatch.setenv("APP32_MCP_OIDC_ADMIN_ROUTE_ENABLED", "1")
    on = {getattr(route, "path", None) for route in http_server.create_http_app().routes}
    assert "/mcp/pilot/admin" in on
    assert "/.well-known/oauth-protected-resource/mcp/pilot/admin" in on
    assert "/mcp/admin" in on, "a superfície legada continua como estava"


def test_discovery_advertises_admin_scope_only_when_enabled(monkeypatch):
    from types import SimpleNamespace

    monkeypatch.setattr(
        http_server,
        "build_auth_settings",
        lambda **kw: SimpleNamespace(resource_server_url="https://x/mcp/pilot/admin", issuer_url="https://id/realms/app32"),
    )
    monkeypatch.setenv("APP32_MCP_OIDC_ADMIN_ROUTE_ENABLED", "1")
    monkeypatch.setattr(http_server, "build_surface_http_app", lambda surface, **kw: Starlette())
    client = TestClient(http_server.create_http_app())
    body = client.get("/.well-known/oauth-protected-resource/mcp/pilot/admin").json()
    assert body["scopes_supported"] == ["mcp:access", "mcp:admin"]
    assert body["resource"].endswith("/mcp/pilot/admin")
