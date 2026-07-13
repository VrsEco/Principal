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


def test_request_identity_supports_db_backed_user_token(monkeypatch):
    module = _reload_auth(monkeypatch)

    class _FakeUserMcpTokenService:
        def resolve_for_http_request(self, **kwargs):
            assert kwargs["company_id"] == 12
            return SimpleNamespace(
                token_record_id=55,
                user_id=7,
                company_id=12,
                fallback_role="colaborador",
                allowed_surfaces=("user",),
                subject="ana@empresa.com",
                client_name="Antigravity",
            )

    from types import SimpleNamespace
    import services.user_mcp_token_service as token_service_module

    monkeypatch.setattr(token_service_module, "user_mcp_token_service", _FakeUserMcpTokenService())

    async def endpoint(request: Request):
        identity = module.resolve_request_identity(request, surface="user")
        return JSONResponse({"user_id": identity.user_id, "company_id": identity.company_id, "client_id": identity.client_id})

    app = Starlette(routes=[])
    app.add_route("/", endpoint)
    client = TestClient(app)

    response = client.get(
        "/?company_id=12",
        headers={"Authorization": "Bearer token-db"},
    )
    assert response.status_code == 200
    assert response.json() == {"user_id": 7, "company_id": 12, "client_id": "app32-mcp-user-token"}


def test_request_context_payload_includes_runtime_profile_and_actor_type(monkeypatch):
    module = _reload_auth(
        monkeypatch,
        APP32_MCP_HTTP_TOKEN="token-123",
        APP32_MCP_USER_ID="3",
        APP32_MCP_COMPANY_ID="9",
        APP32_MCP_FALLBACK_ROLE="colaborador",
        APP32_MCP_HTTP_ALLOW_CONTEXT_OVERRIDE="1",
    )

    async def endpoint(request: Request):
        payload = module.resolve_request_context_payload(request, surface="admin")
        return JSONResponse(payload)

    app = Starlette(routes=[])
    app.add_route("/", endpoint)
    client = TestClient(app)

    response = client.get(
        "/?thread_id=abc&runtime_profile=squad_versus&actor_type=versus_agent",
        headers={"Authorization": "Bearer token-123"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["runtime_profile"] == "squad_versus"
    assert payload["actor_type"] == "versus_agent"
    assert payload["runtime_family"] == "squad_versus"
    assert payload["client_id"] == "app32-mcp-internal"


def test_request_context_payload_exposes_default_harness_for_squad_cliente(monkeypatch):
    module = _reload_auth(monkeypatch)

    class _FakeUserMcpTokenService:
        def resolve_for_http_request(self, **kwargs):
            return SimpleNamespace(
                token_record_id=55,
                user_id=7,
                company_id=12,
                fallback_role="cliente",
                allowed_surfaces=("user",),
                subject="ana@empresa.com",
                client_name="Claude",
                runtime_profile="squad_cliente",
                actor_type="client_agent",
                harness_key="harness_coordenador_cliente_v1",
                harness_label="Harness Coordenador do Squad Cliente",
                mcp_enabled=True,
                training_completed=True,
            )

    from types import SimpleNamespace
    import services.user_mcp_token_service as token_service_module

    monkeypatch.setattr(token_service_module, "user_mcp_token_service", _FakeUserMcpTokenService())

    async def endpoint(request: Request):
        payload = module.resolve_request_context_payload(request, surface="user")
        return JSONResponse(payload)

    app = Starlette(routes=[])
    app.add_route("/", endpoint)
    client = TestClient(app)

    response = client.get("/?company_id=12", headers={"Authorization": "Bearer token-db"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["runtime_family"] == "squad_cliente"
    assert payload["harness_key"] == "harness_coordenador_cliente_v1"
    assert payload["harness_label"] == "Harness Coordenador do Squad Cliente"


def test_request_context_payload_supports_multi_company_user_session_without_active_company(monkeypatch):
    module = _reload_auth(monkeypatch)

    class _FakeUserMcpTokenService:
        def resolve_for_http_request(self, **kwargs):
            return SimpleNamespace(
                token_record_id=55,
                user_id=7,
                company_id=None,
                fallback_role="cliente",
                allowed_surfaces=("user",),
                subject="ana@empresa.com",
                client_name="Claude",
                runtime_profile="squad_cliente",
                actor_type="client_agent",
                harness_key="harness_coordenador_cliente_v1",
                harness_label="Harness Coordenador do Squad Cliente",
                company_resolution_source=None,
                accessible_company_ids=(10, 12),
                multi_company=True,
                mcp_enabled=True,
                training_completed=True,
            )

    from types import SimpleNamespace
    import services.user_mcp_token_service as token_service_module

    monkeypatch.setattr(token_service_module, "user_mcp_token_service", _FakeUserMcpTokenService())

    async def endpoint(request: Request):
        payload = module.resolve_request_context_payload(request, surface="user")
        return JSONResponse(payload)

    app = Starlette(routes=[])
    app.add_route("/", endpoint)
    client = TestClient(app)

    response = client.get("/", headers={"Authorization": "Bearer token-db"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["company_id"] is None
    assert payload["multi_company"] is True
    assert payload["selection_required_for_mutations"] is True
    assert payload["disable_company_fallback"] is True


def test_get_http_request_context_rehydrates_from_current_mcp_request(monkeypatch):
    module = _reload_auth(
        monkeypatch,
        APP32_MCP_HTTP_TOKEN="token-123",
        APP32_MCP_USER_ID="3",
        APP32_MCP_COMPANY_ID="10",
        APP32_MCP_FALLBACK_ROLE="colaborador",
    )

    request = Request(
        {
            "type": "http",
            "method": "POST",
            "scheme": "https",
            "path": "/",
            "root_path": "/mcp/user",
            "query_string": b"company_id=10",
            "headers": [(b"authorization", b"Bearer token-123")],
            "client": ("127.0.0.1", 12345),
            "server": ("app.gestaoversus.com.br", 443),
        }
    )

    monkeypatch.setattr(module, "_get_current_mcp_server_request", lambda: request)

    payload = module.get_http_request_context()

    assert payload is not None
    assert payload["user_id"] == 3
    assert payload["company_id"] == 10
    assert payload["transport"] == "streamable_http"
    assert payload["client"] == "claude_remote_connector"


def test_get_http_request_identity_rehydrates_from_current_mcp_request(monkeypatch):
    module = _reload_auth(
        monkeypatch,
        APP32_MCP_HTTP_TOKEN="token-123",
        APP32_MCP_USER_ID="3",
        APP32_MCP_COMPANY_ID="10",
        APP32_MCP_FALLBACK_ROLE="colaborador",
    )

    request = Request(
        {
            "type": "http",
            "method": "POST",
            "scheme": "https",
            "path": "/",
            "root_path": "/mcp/user",
            "query_string": b"company_id=10",
            "headers": [(b"authorization", b"Bearer token-123")],
            "client": ("127.0.0.1", 12345),
            "server": ("app.gestaoversus.com.br", 443),
        }
    )

    monkeypatch.setattr(module, "_get_current_mcp_server_request", lambda: request)

    identity = module.get_http_request_identity()

    assert identity is not None
    assert identity.user_id == 3
    assert identity.company_id == 10


def test_middleware_rejects_legacy_sse_handshake_without_hanging(monkeypatch):
    module = _reload_auth(
        monkeypatch,
        APP32_MCP_HTTP_TOKEN="token-123",
        APP32_MCP_USER_ID="3",
        APP32_MCP_COMPANY_ID="10",
        APP32_MCP_FALLBACK_ROLE="colaborador",
    )

    async def endpoint(_):
        return JSONResponse({"reached": True})

    app = Starlette(routes=[])
    app.add_route("/", endpoint)
    app.add_middleware(module.App32MCPRequestContextMiddleware, surface="user")
    client = TestClient(app)

    response = client.get(
        "/",
        headers={
            "Authorization": "Bearer token-123",
            "Accept": "text/event-stream",
        },
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"] == "sse_transport_not_supported"
    assert payload["transport"] == "streamable-http"
    assert payload["sse_supported"] is False


def test_middleware_allows_streamable_http_get_when_session_header_exists(monkeypatch):
    module = _reload_auth(
        monkeypatch,
        APP32_MCP_HTTP_TOKEN="token-123",
        APP32_MCP_USER_ID="3",
        APP32_MCP_COMPANY_ID="10",
        APP32_MCP_FALLBACK_ROLE="colaborador",
    )

    async def endpoint(_):
        return JSONResponse({"reached": True})

    app = Starlette(routes=[])
    app.add_route("/", endpoint)
    app.add_middleware(module.App32MCPRequestContextMiddleware, surface="user")
    client = TestClient(app)

    response = client.get(
        "/",
        headers={
            "Authorization": "Bearer token-123",
            "Accept": "text/event-stream",
            "Mcp-Session-Id": "session-1",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"reached": True}


def test_get_http_request_context_rehydrates_even_without_surface_in_scope(monkeypatch):
    module = _reload_auth(
        monkeypatch,
        APP32_MCP_HTTP_TOKEN="token-123",
        APP32_MCP_USER_ID="3",
        APP32_MCP_COMPANY_ID="10",
        APP32_MCP_FALLBACK_ROLE="colaborador",
    )

    request = Request(
        {
            "type": "http",
            "method": "POST",
            "scheme": "https",
            "path": "/",
            "root_path": "",
            "query_string": b"company_id=10",
            "headers": [(b"authorization", b"Bearer token-123")],
            "client": ("127.0.0.1", 12345),
            "server": ("app.gestaoversus.com.br", 443),
        }
    )

    monkeypatch.setattr(module, "_get_current_mcp_server_request", lambda: request)

    payload = module.get_http_request_context()

    assert payload is not None
    assert payload["surface"] == "user"
    assert payload["client"] == "claude_remote_connector"


def test_request_context_middleware_blocks_runtime_profile_surface_mismatch(monkeypatch):
    module = _reload_auth(
        monkeypatch,
        APP32_MCP_HTTP_TOKEN="token-123",
        APP32_MCP_USER_ID="3",
        APP32_MCP_COMPANY_ID="9",
        APP32_MCP_FALLBACK_ROLE="colaborador",
        APP32_MCP_HTTP_ALLOW_CONTEXT_OVERRIDE="1",
    )

    async def endpoint(_: Request):
        return JSONResponse({"ok": True})

    app = Starlette(routes=[])
    app.add_route("/", endpoint)
    app.add_middleware(module.App32MCPRequestContextMiddleware, surface="user")
    client = TestClient(app)

    response = client.get(
        "/?runtime_profile=squad_versus",
        headers={"Authorization": "Bearer token-123"},
    )

    assert response.status_code == 403
    assert response.json()["error"] == "mcp_channel_denied"


def test_request_context_middleware_blocks_when_training_missing(monkeypatch):
    module = _reload_auth(monkeypatch)

    class _FakeUserMcpTokenService:
        def resolve_for_http_request(self, **kwargs):
            return SimpleNamespace(
                token_record_id=55,
                user_id=7,
                company_id=12,
                fallback_role="cliente",
                allowed_surfaces=("user",),
                subject="ana@empresa.com",
                client_name="Claude",
                runtime_profile="squad_cliente",
                actor_type="client_agent",
                mcp_enabled=True,
                training_completed=False,
            )

    from types import SimpleNamespace
    import services.user_mcp_token_service as token_service_module

    monkeypatch.setattr(token_service_module, "user_mcp_token_service", _FakeUserMcpTokenService())

    async def endpoint(_: Request):
        return JSONResponse({"ok": True})

    app = Starlette(routes=[])
    app.add_route("/", endpoint)
    app.add_middleware(module.App32MCPRequestContextMiddleware, surface="user")
    client = TestClient(app)

    response = client.get(
        "/?company_id=12",
        headers={"Authorization": "Bearer token-db"},
    )

    assert response.status_code == 403
    assert response.json()["error"] == "mcp_channel_denied"


def test_request_context_middleware_allows_user_surface_without_active_company(monkeypatch):
    module = _reload_auth(monkeypatch)

    class _FakeUserMcpTokenService:
        def resolve_for_http_request(self, **kwargs):
            return SimpleNamespace(
                token_record_id=55,
                user_id=7,
                company_id=None,
                fallback_role="cliente",
                allowed_surfaces=("user",),
                subject="ana@empresa.com",
                client_name="Claude",
                runtime_profile="squad_cliente",
                actor_type="client_agent",
                accessible_company_ids=(10, 12),
                multi_company=True,
                mcp_enabled=True,
                training_completed=True,
            )

    from types import SimpleNamespace
    import services.user_mcp_token_service as token_service_module

    monkeypatch.setattr(token_service_module, "user_mcp_token_service", _FakeUserMcpTokenService())

    async def endpoint(_: Request):
        return JSONResponse({"ok": True})

    app = Starlette(routes=[])
    app.add_route("/", endpoint)
    app.add_middleware(module.App32MCPRequestContextMiddleware, surface="user")
    client = TestClient(app)

    response = client.get("/", headers={"Authorization": "Bearer token-db"})

    assert response.status_code == 200
    assert response.json() == {"ok": True}

