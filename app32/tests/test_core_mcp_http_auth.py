from __future__ import annotations

import importlib

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.testclient import TestClient

import src.core.mcp_http_auth as auth


def _reload_auth(monkeypatch, **env):
    for key in [
        "APP32_MCP_HTTP_TOKEN",
        "APP32_MCP_HTTP_TOKENS_JSON",
        "APP32_MCP_HTTP_ALLOW_CONTEXT_OVERRIDE",
        "APP32_MCP_USER_ID",
        "APP32_MCP_COMPANY_ID",
        "APP32_MCP_FALLBACK_ROLE",
    ]:
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    auth.load_http_token_registry.cache_clear()
    return importlib.reload(auth)


def test_token_registry_accepts_single_env_token(monkeypatch):
    module = _reload_auth(
        monkeypatch,
        APP32_MCP_HTTP_TOKEN="token-123",
        APP32_MCP_USER_ID="3",
        APP32_MCP_COMPANY_ID="9",
        APP32_MCP_FALLBACK_ROLE="colaborador",
    )

    registry = module.load_http_token_registry()
    assert "token-123" in registry
    identity = registry["token-123"]
    assert identity.user_id == 3
    assert identity.company_id == 9
    assert identity.allows_surface("user")


def test_request_identity_can_override_context_when_enabled(monkeypatch):
    module = _reload_auth(
        monkeypatch,
        APP32_MCP_HTTP_TOKEN="token-123",
        APP32_MCP_USER_ID="3",
        APP32_MCP_COMPANY_ID="9",
        APP32_MCP_HTTP_ALLOW_CONTEXT_OVERRIDE="1",
    )

    async def endpoint(request: Request):
        identity = module.resolve_request_identity(request, surface="user")
        return JSONResponse({"user_id": identity.user_id, "company_id": identity.company_id})

    app = Starlette(routes=[])
    app.add_route("/", endpoint)
    client = TestClient(app)

    response = client.get(
        "/?user_id=7&company_id=11",
        headers={"Authorization": "Bearer token-123"},
    )
    assert response.status_code == 200
    assert response.json() == {"user_id": 7, "company_id": 11}


def test_request_context_middleware_rejects_missing_token(monkeypatch):
    module = _reload_auth(monkeypatch)

    async def endpoint(_: Request):
        return JSONResponse({"ok": True})

    app = Starlette(routes=[])
    app.add_route("/", endpoint)
    app.add_middleware(module.App32MCPRequestContextMiddleware, surface="user")
    client = TestClient(app)

    response = client.get("/")
    assert response.status_code == 401
    assert response.json()["error"] == "unauthorized"

