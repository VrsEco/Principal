import json

from services.oauth_mcp_rollout_readiness_service import (
    evaluate_oauth_mcp_rollout_readiness,
    probe_oauth_mcp_public_endpoints,
)


def valid_pilot_env():
    return {
        "APP32_MCP_USE_PRINCIPAL_GRANTS": "1",
        "APP32_MCP_OIDC_PILOT_ROUTE_ENABLED": "1",
        "APP32_MCP_HTTP_ENABLE_OAUTH": "0",
        "APP32_MCP_OIDC_ISSUER": "https://idp.example/realms/app32",
        "APP32_MCP_OIDC_AUDIENCE": "app32-mcp",
        "APP32_MCP_OIDC_JWKS_URL": "https://idp.example/realms/app32/certs",
        "APP32_MCP_PUBLIC_BASE_URL": "https://hml.example",
        "APP32_MCP_OIDC_ALGORITHMS": "RS256",
        "APP32_MCP_OIDC_REQUIRED_SCOPES": "mcp:access",
        "APP32_MCP_OIDC_ALLOWED_CLIENT_IDS": "codex-pilot",
    }


def test_pilot_readiness_preserves_legacy_surface():
    result = evaluate_oauth_mcp_rollout_readiness(valid_pilot_env(), mode="pilot")
    assert result.ready is True
    assert "legacy user surface preserved" in result.checks
    assert result.blockers == ()


def test_pilot_blocks_accidental_user_cohort_cutover():
    env = valid_pilot_env()
    env.update({"APP32_MCP_HTTP_ENABLE_OAUTH": "1", "APP32_MCP_OIDC_ENABLED_SURFACES": "user"})
    result = evaluate_oauth_mcp_rollout_readiness(env, mode="pilot")
    assert result.ready is False
    assert "pilot cannot replace the legacy user surface" in result.blockers


def test_readiness_fails_closed_for_http_or_missing_grant_gate():
    env = valid_pilot_env()
    env["APP32_MCP_USE_PRINCIPAL_GRANTS"] = "0"
    env["APP32_MCP_OIDC_JWKS_URL"] = "http://idp.example/certs"
    result = evaluate_oauth_mcp_rollout_readiness(env, mode="pilot")
    assert result.ready is False
    assert "APP32_MCP_USE_PRINCIPAL_GRANTS must be enabled" in result.blockers
    assert "APP32_MCP_OIDC_JWKS_URL must use HTTPS" in result.blockers


def test_cohort_requires_explicit_surface_and_access_scope():
    env = valid_pilot_env()
    env.update({
        "APP32_MCP_HTTP_ENABLE_OAUTH": "1",
        "APP32_MCP_OIDC_ENABLED_SURFACES": "",
        "APP32_MCP_OIDC_REQUIRED_SCOPES": "openid",
    })
    result = evaluate_oauth_mcp_rollout_readiness(env, mode="cohort")
    assert result.ready is False
    assert "APP32_MCP_OIDC_ENABLED_SURFACES must name an explicit cohort" in result.blockers
    assert "APP32_MCP_OIDC_REQUIRED_SCOPES must include mcp:access" in result.blockers


def test_dynamic_registration_without_allowlist_is_explicit_warning():
    env = valid_pilot_env()
    env["APP32_MCP_OIDC_ALLOWED_CLIENT_IDS"] = ""
    result = evaluate_oauth_mcp_rollout_readiness(env, mode="pilot")
    assert result.ready is True
    assert result.warnings == (
        "client allowlist is empty; acceptable only for approved dynamic registration",
    )


def test_live_probe_requires_matching_discovery_jwks_and_resource_metadata():
    env = valid_pilot_env()
    payloads = {
        "https://idp.example/realms/app32/.well-known/openid-configuration": {
            "issuer": env["APP32_MCP_OIDC_ISSUER"],
            "jwks_uri": env["APP32_MCP_OIDC_JWKS_URL"],
        },
        env["APP32_MCP_OIDC_JWKS_URL"]: {
            "keys": [{"kid": "key-1", "kty": "RSA"}],
        },
        "https://hml.example/.well-known/oauth-protected-resource/mcp/pilot/user": {
            "resource": "https://hml.example/mcp/pilot/user",
            "authorization_servers": [env["APP32_MCP_OIDC_ISSUER"]],
        },
    }

    class Response:
        status = 200
        def __init__(self, payload):
            self.payload = payload
        def __enter__(self):
            return self
        def __exit__(self, *_):
            return None
        def read(self, _limit):
            return json.dumps(self.payload).encode()

    def opener(request, **_):
        return Response(payloads[request.full_url])

    probe = probe_oauth_mcp_public_endpoints(env, opener=opener)
    assert probe.ready is True
    assert len(probe.checks) == 3


def test_live_probe_fails_closed_on_discovery_drift():
    env = valid_pilot_env()

    class Response:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *_): return None
        def read(self, _limit):
            return json.dumps({"issuer": "https://attacker.invalid", "jwks_uri": "https://attacker.invalid/jwks"}).encode()

    probe = probe_oauth_mcp_public_endpoints(env, opener=lambda *_args, **_kwargs: Response())
    assert probe.ready is False
    assert "OIDC discovery issuer/jwks_uri differs from server configuration" in probe.blockers
