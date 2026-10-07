"""Request freshness regressions using synthetic MCP requests and identities.

No factory, database, network, real credential or browser session is used.
The verified fallback is injected: these tests do not validate real OAuth.
"""
import asyncio
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest
from starlette.requests import Request
from starlette.responses import JSONResponse


ROOT = Path(__file__).resolve().parents[1]
MODULE_NAME = "_app32_mcp_request_freshness_isolated"
spec = importlib.util.spec_from_file_location(MODULE_NAME, ROOT / "src/core/mcp_http_auth.py")
auth = importlib.util.module_from_spec(spec)
sys.modules[MODULE_NAME] = auth
saved_path = list(sys.path)
try:
    sys.path.insert(0, str(ROOT))
    spec.loader.exec_module(auth)
finally:
    sys.path[:] = saved_path

def _run_async(coro):
    """Run in a private thread/loop so a loop leaked by other tests cannot interfere."""
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result()


def _identity(*, user_id, principal_id, company_id, role, scopes, issuer, client):
    return auth.App32McpHttpIdentity(
        token="synthetic-unit-test-token", user_id=user_id, principal_id=principal_id,
        company_id=company_id, fallback_role=role, allowed_surfaces=("analytics",),
        issuer=issuer, subject=f"fixture-user-{user_id}", auth_method="oauth",
        scopes=scopes, client_id=client,
    )


def _request(**scope_fields):
    scope = {"type": "http", "asgi": {"version": "3.0"}, "method": "POST",
             "scheme": "http", "path": "/mcp/analytics", "raw_path": b"/mcp/analytics",
             "root_path": "", "query_string": b"", "headers": [],
             "client": ("127.0.0.1", 10000), "server": ("127.0.0.1", 8101)}
    scope.update(scope_fields)
    return Request(scope)


@pytest.fixture
def identities():
    initialized = _identity(user_id=99, principal_id=999, company_id=88, role="administrador",
                            scopes=("mcp:access", "mcp:admin"), issuer="https://initialize.invalid",
                            client="initialize-client")
    current = _identity(user_id=3, principal_id=30, company_id=9, role="colaborador",
                        scopes=("mcp:access", "mcp:analytics"), issuer="https://current.invalid",
                        client="current-client")
    initialized_payload = {"user_id": 99, "principal_id": 999, "company_id": 88,
                           "fallback_role": "administrador", "token_scopes": ["mcp:access", "mcp:admin"],
                           "issuer": initialized.issuer, "client_id": initialized.client_id, "surface": "admin"}
    current_payload = {"user_id": 3, "principal_id": 30, "company_id": 9,
                       "fallback_role": "colaborador", "token_scopes": ["mcp:access", "mcp:analytics"],
                       "issuer": current.issuer, "client_id": current.client_id, "surface": "analytics"}
    return initialized, current, initialized_payload, current_payload


@pytest.fixture
def inherited_context(identities):
    initialized, _, initialized_payload, _ = identities
    tokens = auth.set_http_request_context(initialized, initialized_payload)
    try:
        yield
    finally:
        auth.reset_http_request_context(tokens)


def _forbidden(*args, **kwargs):
    raise AssertionError("Verified current scope must win before inherited/fallback identity")


def test_current_verified_projection_overrides_initialize_principal_company_scopes_and_role(
        monkeypatch, identities, inherited_context):
    _, current, _, payload = identities
    request = _request(app32_mcp_context=dict(payload), app32_mcp_identity=current)
    monkeypatch.setattr(auth, "_get_current_mcp_server_request", lambda: request)
    monkeypatch.setattr(auth, "_resolve_identity_from_current_request", _forbidden)
    assert auth.get_http_request_context() == payload
    assert auth.get_http_actor_role() == "colaborador"
    assert auth.get_http_request_context()["principal_id"] == 30
    assert auth.get_http_request_context()["company_id"] == 9
    assert auth.get_http_request_context()["token_scopes"] == ["mcp:access", "mcp:analytics"]


def test_current_verified_identity_marker_overrides_initialize_user_issuer_and_client(
        monkeypatch, identities, inherited_context):
    _, current, _, _ = identities
    request = _request(app32_mcp_identity=current)
    monkeypatch.setattr(auth, "_get_current_mcp_server_request", lambda: request)
    monkeypatch.setattr(auth, "_resolve_identity_from_current_request", _forbidden)
    assert auth.get_http_request_identity() is current
    assert auth.get_http_request_identity().user_id == 3
    assert auth.get_http_request_identity().issuer == "https://current.invalid"
    assert auth.get_http_request_identity().client_id == "current-client"


def test_current_context_is_a_copy_of_verified_server_projection(monkeypatch, identities, inherited_context):
    _, _, _, payload = identities
    request = _request(app32_mcp_context=dict(payload))
    monkeypatch.setattr(auth, "_get_current_mcp_server_request", lambda: request)
    result = auth.get_http_request_context()
    result["company_id"] = 999
    assert request.scope["app32_mcp_context"]["company_id"] == 9


def test_missing_current_projection_uses_only_current_verified_identity_and_payload(
        monkeypatch, identities, inherited_context):
    _, current, _, payload = identities
    request = _request()
    observed = []
    def verified(request_value, *, surface, oauth_enabled=None):
        observed.append((request_value, surface))
        return current
    def current_payload(request_value, *, surface, oauth_enabled=None):
        assert request_value is request and surface == "analytics"
        return dict(payload)
    monkeypatch.setattr(auth, "_get_current_mcp_server_request", lambda: request)
    monkeypatch.setattr(auth, "resolve_request_identity", verified)
    monkeypatch.setattr(auth, "resolve_request_context_payload", current_payload)
    assert auth.get_http_request_context() == payload
    assert observed == [(request, "analytics")]


def test_missing_current_identity_marker_revalidates_current_bearer(monkeypatch, identities, inherited_context):
    _, current, _, _ = identities
    request = _request()
    monkeypatch.setattr(auth, "_get_current_mcp_server_request", lambda: request)
    monkeypatch.setattr(auth, "resolve_request_identity", lambda current_request, **kwargs: current)
    assert auth.get_http_request_identity() is current


@pytest.mark.parametrize("getter", ["get_http_request_context", "get_http_request_identity"])
def test_current_denied_bearer_never_inherits_initialize_context(monkeypatch, inherited_context, getter):
    request = _request()
    monkeypatch.setattr(auth, "_get_current_mcp_server_request", lambda: request)
    monkeypatch.setattr(auth, "resolve_request_identity", lambda *args, **kwargs: None)
    monkeypatch.setattr(auth, "_resolve_identity_from_mcp_auth_context", _forbidden)
    assert getattr(auth, getter)() is None


@pytest.mark.parametrize("invalid_projection", [[], ["initialize"], "not-server-context", 99, True])
def test_invalid_current_context_projection_cannot_reuse_initialize_context(
        monkeypatch, inherited_context, invalid_projection):
    request = _request(app32_mcp_context=invalid_projection)
    monkeypatch.setattr(auth, "_get_current_mcp_server_request", lambda: request)
    monkeypatch.setattr(auth, "resolve_request_identity", lambda *args, **kwargs: None)
    assert auth.get_http_request_context() is None


@pytest.mark.parametrize("invalid_marker", [{"user_id": 99}, "initialize-identity", 99, True])
def test_invalid_identity_marker_cannot_reuse_initialize_identity(monkeypatch, inherited_context, invalid_marker):
    request = _request(app32_mcp_identity=invalid_marker)
    monkeypatch.setattr(auth, "_get_current_mcp_server_request", lambda: request)
    monkeypatch.setattr(auth, "resolve_request_identity", lambda *args, **kwargs: None)
    assert auth.get_http_request_identity() is None


@pytest.mark.parametrize("getter", ["get_http_request_context", "get_http_request_identity"])
def test_current_identity_verification_exceptions_deny_without_initialize_fallback(
        monkeypatch, inherited_context, getter):
    def failed_verification(*args, **kwargs):
        raise RuntimeError("synthetic verifier failure")
    monkeypatch.setattr(auth, "_get_current_mcp_server_request", lambda: _request())
    monkeypatch.setattr(auth, "resolve_request_identity", failed_verification)
    monkeypatch.setattr(auth, "_resolve_identity_from_mcp_auth_context", _forbidden)
    assert getattr(auth, getter)() is None


def test_current_payload_resolution_exception_denies_without_initialize_fallback(
        monkeypatch, identities, inherited_context):
    _, current, _, _ = identities
    monkeypatch.setattr(auth, "_get_current_mcp_server_request", lambda: _request())
    monkeypatch.setattr(auth, "resolve_request_identity", lambda *args, **kwargs: current)
    def failure(*args, **kwargs):
        raise RuntimeError("synthetic payload failure")
    monkeypatch.setattr(auth, "resolve_request_context_payload", failure)
    assert auth.get_http_request_context() is None


def test_empty_current_projection_and_denied_bearer_cannot_inherit_initialize(monkeypatch, inherited_context):
    request = _request(app32_mcp_context={})
    monkeypatch.setattr(auth, "_get_current_mcp_server_request", lambda: request)
    monkeypatch.setattr(auth, "resolve_request_identity", lambda *args, **kwargs: None)
    assert auth.get_http_request_context() is None


def test_without_current_sdk_request_legacy_contextvars_are_preserved(monkeypatch, identities, inherited_context):
    initialized, _, payload, _ = identities
    monkeypatch.setattr(auth, "_get_current_mcp_server_request", lambda: None)
    monkeypatch.setattr(auth, "_resolve_identity_from_mcp_auth_context", _forbidden)
    assert auth.get_http_request_identity() is initialized
    assert auth.get_http_request_context() == payload
    assert auth.get_http_actor_role() == "administrador"


def test_without_sdk_request_or_contextvars_sdk_access_token_path_is_preserved(monkeypatch, identities):
    import mcp.server.auth.middleware.auth_context as sdk_auth
    _, current, _, _ = identities
    identity_token = auth._http_identity_ctx.set(None)
    context_token = auth._http_request_ctx.set(None)
    try:
        monkeypatch.setattr(auth, "_get_current_mcp_server_request", lambda: None)
        monkeypatch.setattr(sdk_auth, "get_access_token", lambda: SimpleNamespace(
            token="synthetic-unit-test-token", resource="mcp:analytics"))
        monkeypatch.setattr(auth, "load_http_token_registry", lambda: {"synthetic-unit-test-token": current})
        monkeypatch.setattr(auth, "_resolve_db_backed_identity", _forbidden)
        assert auth.get_http_request_identity() is current
        payload = auth.get_http_request_context()
        assert payload["user_id"] == 3 and payload["principal_id"] == 30
        assert payload["company_id"] == 9 and payload["surface"] == "analytics"
    finally:
        auth._http_identity_ctx.reset(identity_token)
        auth._http_request_ctx.reset(context_token)


def test_middleware_projects_verified_identity_and_context_in_current_request_scope(monkeypatch, identities):
    _, current, _, payload = identities
    request = _request()
    monkeypatch.setattr(auth, "resolve_request_identity", lambda *args, **kwargs: current)
    monkeypatch.setattr(auth, "resolve_request_context_payload", lambda *args, **kwargs: dict(payload))
    monkeypatch.setattr(auth, "evaluate_mcp_channel_gate", lambda *args, **kwargs: SimpleNamespace(allowed=True))
    async def application(scope, receive, send):
        raise AssertionError("Direct middleware dispatch uses only the synthetic callback")
    middleware = auth.App32MCPRequestContextMiddleware(application, surface="analytics", oauth_enabled=False)
    async def endpoint(current_request):
        assert current_request.scope["app32_mcp_identity"] is current
        assert current_request.scope["app32_mcp_context"] == payload
        return JSONResponse({"scope_identity_verified": True})
    response = _run_async(middleware.dispatch(request, endpoint))
    assert response.status_code == 200
    assert request.scope["app32_mcp_identity"] is current
    assert request.scope["app32_mcp_context"] == payload
