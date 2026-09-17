from pathlib import Path


def _values():
    env_file = Path(__file__).parents[1] / ".env.example"
    result = {}
    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        result[name] = value
    return result


def test_oauth_example_is_fail_closed_and_contains_no_runtime_credential():
    values = _values()
    assert values["APP32_MCP_HTTP_ENABLE_OAUTH"] == "0"
    assert values["APP32_MCP_OIDC_PILOT_ROUTE_ENABLED"] == "0"
    assert values["APP32_MCP_USE_PRINCIPAL_GRANTS"] == "0"
    assert values["APP32_MCP_OIDC_ENABLED_SURFACES"] == ""
    assert values["APP32_MCP_PUBLIC_BASE_URL"] == ""
    assert values["APP32_MCP_OIDC_ISSUER"] == ""
    assert values["APP32_MCP_OIDC_JWKS_URL"] == ""
    assert values["APP32_MCP_OIDC_ALGORITHMS"] == "RS256"
    assert values["APP32_MCP_OIDC_REQUIRED_SCOPES"] == "mcp:access"
    assert not any(
        name.startswith("APP32_MCP_OIDC_")
        and any(term in name for term in ("ACCESS_TOKEN", "REFRESH_TOKEN", "CLIENT_SECRET", "PRIVATE_KEY"))
        for name in values
    )
