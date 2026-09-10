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
        "APP32_MCP_PRINCIPAL_ID",
        "APP32_MCP_FALLBACK_ROLE",
        "APP32_MCP_HTTP_ENABLE_OAUTH",
        "APP32_MCP_OIDC_ENABLED_SURFACES",
        "APP32_MCP_USE_PRINCIPAL_GRANTS",
        "APP32_MCP_OIDC_ISSUER",
        "APP32_MCP_OIDC_AUDIENCE",
        "APP32_MCP_OIDC_JWKS_URL",
        "APP32_MCP_OIDC_ALLOWED_CLIENT_IDS",
        "APP32_MCP_OIDC_REQUIRED_SCOPES",
        "APP32_MCP_PUBLIC_BASE_URL",
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
        APP32_MCP_PRINCIPAL_ID="71",
        APP32_MCP_FALLBACK_ROLE="colaborador",
    )

    registry = module.load_http_token_registry()
    assert "token-123" in registry
    identity = registry["token-123"]
    assert identity.user_id == 3
    assert identity.company_id == 9
    assert identity.principal_id == 71
    assert identity.allows_surface("user")


def test_request_context_payload_propagates_server_side_principal_id(monkeypatch):
    module = _reload_auth(
        monkeypatch,
        APP32_MCP_HTTP_TOKEN="token-123",
        APP32_MCP_USER_ID="3",
        APP32_MCP_COMPANY_ID="9",
        APP32_MCP_PRINCIPAL_ID="71",
    )

    async def endpoint(request: Request):
        return JSONResponse(module.resolve_request_context_payload(request, surface="user"))

    app = Starlette(routes=[])
    app.add_route("/", endpoint)
    client = TestClient(app)

    response = client.get(
        "/?principal_id=999",
        headers={"Authorization": "Bearer token-123", "x-app32-principal-id": "999"},
    )

    assert response.status_code == 200
    assert response.json()["principal_id"] == 71


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


def test_db_backed_token_never_accepts_role_from_request(monkeypatch):
    module = _reload_auth(monkeypatch, APP32_MCP_HTTP_ALLOW_CONTEXT_OVERRIDE="1")

    class _FakeUserMcpTokenService:
        def resolve_for_http_request(self, **kwargs):
            assert kwargs["company_id"] == 12
            return SimpleNamespace(
                token_record_id=56,
                user_id=7,
                company_id=12,
                fallback_role="colaborador",
                allowed_surfaces=("user",),
                subject="ana@empresa.com",
                client_name="Codex",
            )

    from types import SimpleNamespace
    import services.user_mcp_token_service as token_service_module

    monkeypatch.setattr(token_service_module, "user_mcp_token_service", _FakeUserMcpTokenService())

    async def endpoint(request: Request):
        identity = module.resolve_request_identity(request, surface="user")
        return JSONResponse({"fallback_role": identity.fallback_role})

    app = Starlette(routes=[])
    app.add_route("/", endpoint)
    client = TestClient(app)

    response = client.get(
        "/?company_id=12&fallback_role=administrador",
        headers={
            "Authorization": "Bearer token-db",
            "x-app32-fallback-role": "administrador_tecnico",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"fallback_role": "colaborador"}


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


def _enable_local_oauth_cohort(monkeypatch, **overrides):
    values = {
        "APP32_MCP_HTTP_ENABLE_OAUTH": "1",
        "APP32_MCP_OIDC_ENABLED_SURFACES": "user",
        "APP32_MCP_USE_PRINCIPAL_GRANTS": "1",
        "APP32_MCP_PUBLIC_BASE_URL": "https://mcp.local.test",
    }
    values.update(overrides)
    return _reload_auth(monkeypatch, **values)


def _stub_oauth_resolution(monkeypatch, module, *, scopes=("mcp:access", "mcp:user"), principal_id=71, user_id=7):
    from types import SimpleNamespace
    from services.principal_authorization_service import principal_authorization_service

    class _Verifier:
        def verify(self, token):
            assert token == "oauth-token"
            return SimpleNamespace(
                issuer="https://keycloak.local/realms/app32-local",
                subject="service:local-smoke",
                scopes=tuple(scopes),
                client_id="mcp-local-service",
                expires_at=4_102_444_800,
            )

    class _PrincipalService:
        def resolve_external_principal(self, *, issuer, subject):
            assert issuer == "https://keycloak.local/realms/app32-local"
            assert subject == "service:local-smoke"
            principal = SimpleNamespace(
                id=principal_id,
                user_id=user_id,
                subject_type="SERVICE" if user_id is None else "USER",
            )
            return SimpleNamespace(allowed=True, principal=principal)

    monkeypatch.setattr(module, "load_oauth_access_token_verifier", lambda: _Verifier())
    monkeypatch.setattr(
        "services.principal_authorization_service.principal_authorization_service",
        _PrincipalService(),
    )
    return principal_authorization_service


def test_oauth_cohort_resolves_only_verified_linked_principal(monkeypatch):
    module = _enable_local_oauth_cohort(monkeypatch)
    _stub_oauth_resolution(monkeypatch, module, principal_id=71, user_id=None)

    async def endpoint(request: Request):
        identity = module.resolve_request_identity(request, surface="user")
        return JSONResponse(
            {
                "principal_id": identity.principal_id,
                "user_id": identity.user_id,
                "company_id": identity.company_id,
                "subject_type": identity.subject_type,
                "auth_method": identity.auth_method,
                "scopes": list(identity.scopes),
            }
        )

    app = Starlette(routes=[])
    app.add_route("/", endpoint)
    app.add_middleware(module.App32MCPRequestContextMiddleware, surface="user")

    response = TestClient(app).get(
        "/?company_id=999&fallback_role=administrador",
        headers={"Authorization": "Bearer oauth-token"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "principal_id": 71,
        "user_id": None,
        "company_id": None,
        "subject_type": "SERVICE",
        "auth_method": "oauth_oidc_bearer",
        "scopes": ["mcp:access", "mcp:user"],
    }


def test_oauth_cohort_never_falls_back_to_legacy_registry_after_rejection(monkeypatch):
    module = _enable_local_oauth_cohort(monkeypatch, APP32_MCP_HTTP_TOKEN="oauth-token")

    class _RejectingVerifier:
        def verify(self, _token):
            raise module.OAuthTokenVerificationError("assinatura rejeitada")

    monkeypatch.setattr(module, "load_oauth_access_token_verifier", lambda: _RejectingVerifier())

    async def endpoint(_: Request):
        return JSONResponse({"reached": True})

    app = Starlette(routes=[])
    app.add_route("/", endpoint)
    app.add_middleware(module.App32MCPRequestContextMiddleware, surface="user")
    response = TestClient(app).get("/", headers={"Authorization": "Bearer oauth-token"})

    assert response.status_code == 401
    assert response.json()["error"] == "invalid_token"
    assert "resource_metadata=\"https://mcp.local.test/.well-known/oauth-protected-resource/mcp/user\"" in response.headers[
        "WWW-Authenticate"
    ]


def test_oauth_cohort_returns_403_for_missing_surface_scope(monkeypatch):
    module = _enable_local_oauth_cohort(monkeypatch)
    _stub_oauth_resolution(monkeypatch, module, scopes=("mcp:access",))

    async def endpoint(_: Request):
        return JSONResponse({"reached": True})

    app = Starlette(routes=[])
    app.add_route("/", endpoint)
    app.add_middleware(module.App32MCPRequestContextMiddleware, surface="user")
    response = TestClient(app).get("/", headers={"Authorization": "Bearer oauth-token"})

    assert response.status_code == 403
    assert response.json()["error"] == "insufficient_scope"
    assert "mcp:user" in response.headers["WWW-Authenticate"]


def test_oauth_technical_principal_can_reach_non_user_surface_without_token_tenant(monkeypatch):
    module = _enable_local_oauth_cohort(monkeypatch, APP32_MCP_OIDC_ENABLED_SURFACES="ops")
    _stub_oauth_resolution(monkeypatch, module, scopes=("mcp:access", "mcp:ops"), user_id=None)

    async def endpoint(_: Request):
        return JSONResponse({"reached": True})

    app = Starlette(routes=[])
    app.add_route("/", endpoint)
    app.add_middleware(module.App32MCPRequestContextMiddleware, surface="ops")
    response = TestClient(app).get("/", headers={"Authorization": "Bearer oauth-token"})

    assert response.status_code == 200
    assert response.json() == {"reached": True}


def test_oauth_sdk_verifier_exposes_subject_and_expiry_without_registry_fallback(monkeypatch):
    import asyncio

    module = _enable_local_oauth_cohort(monkeypatch)
    _stub_oauth_resolution(monkeypatch, module, principal_id=71, user_id=7)

    access_token = asyncio.run(module.App32MCPTokenVerifier(surface="user").verify_token("oauth-token"))

    assert access_token is not None
    assert access_token.client_id == "mcp-local-service"
    assert access_token.subject == "service:local-smoke"
    assert access_token.expires_at == 4_102_444_800
    assert access_token.claims == {"iss": "https://keycloak.local/realms/app32-local"}


def test_legacy_token_remains_available_outside_explicit_oauth_surface_cohort(monkeypatch):
    module = _reload_auth(
        monkeypatch,
        APP32_MCP_HTTP_ENABLE_OAUTH="1",
        APP32_MCP_OIDC_ENABLED_SURFACES="admin",
        APP32_MCP_HTTP_TOKEN="legacy-user-token",
        APP32_MCP_USER_ID="3",
        APP32_MCP_COMPANY_ID="9",
    )

    request = Request(
        {
            "type": "http",
            "method": "GET",
            "scheme": "https",
            "path": "/",
            "root_path": "/mcp/user",
            "query_string": b"",
            "headers": [(b"authorization", b"Bearer legacy-user-token")],
            "client": ("127.0.0.1", 12345),
            "server": ("mcp.local.test", 443),
        }
    )

    identity = module.resolve_request_identity(request, surface="user")

    assert identity is not None
    assert identity.auth_method == "internal_bearer"
    assert identity.user_id == 3
    assert identity.company_id == 9


def test_oauth_cohort_resource_metadata_points_to_external_idp(monkeypatch):
    from types import SimpleNamespace

    module = _enable_local_oauth_cohort(monkeypatch)
    verifier_settings = SimpleNamespace(issuer="https://keycloak.local/realms/app32-local")
    monkeypatch.setattr(
        module,
        "load_oauth_access_token_verifier",
        lambda: SimpleNamespace(settings=verifier_settings),
    )

    settings = module.build_auth_settings(
        base_url="https://mcp.local.test/mcp/user",
        surface="user",
    )

    assert str(settings.issuer_url) == "https://keycloak.local/realms/app32-local"
    assert str(settings.resource_server_url) == "https://mcp.local.test/mcp/user"
    assert settings.required_scopes == ["mcp:access"]


def test_legacy_surface_does_not_advertise_external_issuer_from_another_cohort(monkeypatch):
    module = _reload_auth(
        monkeypatch,
        APP32_MCP_HTTP_ENABLE_OAUTH="1",
        APP32_MCP_OIDC_ENABLED_SURFACES="admin",
        APP32_MCP_OIDC_ISSUER="https://keycloak.local/realms/app32-local",
    )

    settings = module.build_auth_settings(
        base_url="https://mcp.local.test/mcp/user",
        surface="user",
    )

    assert str(settings.issuer_url) == "https://mcp.local.test/mcp/user"


def test_oauth_http_context_enforces_principal_grant_for_requested_company(monkeypatch):
    from types import SimpleNamespace
    from src.core.mcp_runtime import resolve_mcp_execution_context

    module = _enable_local_oauth_cohort(monkeypatch)

    class _Verifier:
        def verify(self, token):
            assert token == "oauth-token"
            return SimpleNamespace(
                issuer="https://keycloak.local/realms/app32-local",
                subject="user:ana",
                scopes=("mcp:access", "mcp:user"),
                client_id="mcp-local-user",
                expires_at=4_102_444_800,
            )

    class _PrincipalService:
        def resolve_external_principal(self, *, issuer, subject):
            assert (issuer, subject) == ("https://keycloak.local/realms/app32-local", "user:ana")
            return SimpleNamespace(
                allowed=True,
                principal=SimpleNamespace(id=71, user_id=7, subject_type="USER"),
            )

        def resolve_for_company(self, *, principal_id, company_id):
            assert principal_id == 71
            if company_id == 9:
                return SimpleNamespace(
                    allowed=True,
                    company_id=9,
                    role="cliente",
                    principal=SimpleNamespace(user_id=7),
                )
            return SimpleNamespace(allowed=False, reason="grant do principal para a empresa não encontrado")

    monkeypatch.setattr(module, "load_oauth_access_token_verifier", lambda: _Verifier())
    monkeypatch.setattr(
        "services.principal_authorization_service.principal_authorization_service",
        _PrincipalService(),
    )
    monkeypatch.setattr(
        "src.core.mcp_runtime.resolve_runtime_identity",
        lambda user_id, company_id: {
            "employee_id": 27,
            "company_id": company_id,
            "role": "administrador",
            "permissions": {"finance": ["write"]},
            "accessible_company_ids": [company_id],
        },
    )

    async def endpoint(request: Request):
        try:
            context = resolve_mcp_execution_context({"company_id": request.query_params.get("company_id")})
        except PermissionError:
            return JSONResponse({"error": "tenant_denied"}, status_code=403)
        return JSONResponse(
            {
                "company_id": context.company_id,
                "principal_id": context.principal_id,
                "role": context.role,
                "permissions": list(context.permissions),
                "grant_enforced": context.metadata["principal_grant_enforced"],
            }
        )

    app = Starlette(routes=[])
    app.add_route("/", endpoint)
    app.add_middleware(module.App32MCPRequestContextMiddleware, surface="user")
    client = TestClient(app)

    allowed = client.get("/?company_id=9", headers={"Authorization": "Bearer oauth-token"})
    denied = client.get("/?company_id=10", headers={"Authorization": "Bearer oauth-token"})

    assert allowed.status_code == 200
    assert allowed.json() == {
        "company_id": 9,
        "principal_id": 71,
        "role": "cliente",
        "permissions": [],
        "grant_enforced": True,
    }
    assert denied.status_code == 403
    assert denied.json() == {"error": "tenant_denied"}



def test_request_context_rehydrates_from_mcp_auth_task_context(monkeypatch):
    module = _reload_auth(monkeypatch)
    identity = module.App32McpHttpIdentity(
        token="token-db",
        user_id=90,
        company_id=9,
        fallback_role="administrador",
        allowed_surfaces=("user",),
        metadata={
            "runtime_profile": "squad_cliente",
            "actor_type": "client_agent",
            "harness_key": "harness_coordenador_cliente_v1",
            "accessible_company_ids": [9, 12],
            "multi_company": True,
        },
    )
    monkeypatch.setattr(
        module,
        "_resolve_identity_from_mcp_auth_context",
        lambda: (identity, "user"),
    )

    payload = module.get_http_request_context()

    assert payload["user_id"] == 90
    assert payload["company_id"] == 9
    assert payload["fallback_role"] == "administrador"
    assert payload["runtime_profile"] == "squad_cliente"
    assert payload["harness_key"] == "harness_coordenador_cliente_v1"
    assert module.get_http_actor_role() == "administrador"


def test_request_context_rehydrates_from_transport_scope_bridge(monkeypatch):
    module = _reload_auth(monkeypatch)
    expected = {
        "user_id": 90,
        "company_id": 9,
        "fallback_role": "administrador",
        "surface": "user",
        "runtime_profile": "squad_cliente",
        "harness_key": "harness_coordenador_cliente_v1",
    }
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "scheme": "https",
            "path": "/",
            "root_path": "/mcp/user",
            "query_string": b"",
            "headers": [],
            "client": ("127.0.0.1", 12345),
            "server": ("app.gestaoversus.com.br", 443),
            "app32_mcp_context": expected,
        }
    )
    monkeypatch.setattr(module, "_resolve_identity_from_mcp_auth_context", lambda: (None, None))
    monkeypatch.setattr(module, "_get_current_mcp_server_request", lambda: request)

    assert module.get_http_request_context() == expected


def test_request_context_middleware_returns_retryable_503_during_runtime_restart(monkeypatch):
    module = _reload_auth(
        monkeypatch,
        APP32_MCP_HTTP_TOKEN="token-123",
        APP32_MCP_USER_ID="3",
        APP32_MCP_COMPANY_ID="9",
        APP32_MCP_FALLBACK_ROLE="colaborador",
    )

    async def endpoint(_: Request):
        raise RuntimeError("No response returned.")

    app = Starlette(routes=[])
    app.add_route("/", endpoint)
    app.add_middleware(module.App32MCPRequestContextMiddleware, surface="user")
    response = TestClient(app, raise_server_exceptions=False).get(
        "/", headers={"Authorization": "Bearer token-123"}
    )

    assert response.status_code == 503
    assert response.headers["Retry-After"] == "2"
    assert response.json()["error"] == "mcp_runtime_temporarily_unavailable"
    assert response.json()["retryable"] is True
