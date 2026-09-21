from services.mcp_versus_oauth_connector_service import McpVersusOAuthConnectorService


def test_mcp_versus_is_the_fixed_public_connection_name(monkeypatch):
    monkeypatch.setenv("MCP_VERSUS_OAUTH_CODEX_ENABLED", "1")
    monkeypatch.setenv("MCP_VERSUS_OAUTH_CODEX_CLIENT_ID", "mcp-versus-codex")

    payload = McpVersusOAuthConnectorService().build_config("codex")

    assert payload["server_name"] == "mcp-versus"
    assert payload["client_id"] == "mcp-versus-codex"
    assert payload["add_command"].startswith("codex mcp add mcp-versus ")
    assert "company_id" not in payload


def test_mcp_versus_codex_uses_unified_endpoint_when_enabled(monkeypatch):
    monkeypatch.setenv("MCP_VERSUS_OAUTH_CODEX_ENABLED", "1")
    monkeypatch.setenv("MCP_VERSUS_OAUTH_CODEX_CLIENT_ID", "mcp-versus-codex")
    monkeypatch.setenv("MCP_VERSUS_OAUTH_UNIFIED_ENABLED", "1")

    payload = McpVersusOAuthConnectorService().build_config("codex")

    assert payload["server_name"] == "mcp-versus"
    assert payload["mcp_url"].endswith("/mcp/pilot/")
    assert "--scopes mcp:access,mcp:user,mcp:analytics,mcp:finance" in payload["login_command"]


def test_claude_configuration_uses_dcr_without_exposing_a_static_client_id(monkeypatch):
    monkeypatch.setenv("MCP_VERSUS_OAUTH_CLAUDE_ENABLED", "1")
    monkeypatch.setenv("MCP_VERSUS_OAUTH_CLAUDE_CLIENT_ID", "mcp-versus-claude")
    monkeypatch.setenv("MCP_VERSUS_OAUTH_CLAUDE_DCR_READY", "1")

    payload = McpVersusOAuthConnectorService().build_config("claude")

    assert payload["available"] is True
    assert payload["server_name"] == "mcp-versus"
    assert payload["registration_mode"] == "dynamic"
    assert "client_id" not in payload
    assert payload["redirect_uri"] == "https://claude.ai/api/mcp/auth_callback"
    assert not any("token" in str(key).lower() for key in payload)
    assert any("client ID, token, scope, host" in item for item in payload["instructions"])
    assert any("Claude Desktop possui homologação própria" in item for item in payload["instructions"])


def test_antigravity_configuration_has_oauth_client_id(monkeypatch):
    monkeypatch.setenv("MCP_VERSUS_OAUTH_ANTIGRAVITY_ENABLED", "1")
    monkeypatch.setenv("MCP_VERSUS_OAUTH_ANTIGRAVITY_CLIENT_ID", "mcp-versus-antigravity")

    payload = McpVersusOAuthConnectorService().build_config("antigravity")

    config = payload["config_json"]
    assert config["mcpServers"]["mcp-versus"]["serverUrl"].endswith("/mcp/pilot/user/")
    assert config["mcpServers"]["mcp-versus"]["oauth"]["clientId"] == "mcp-versus-antigravity"
    assert payload["redirect_uri"] == "https://antigravity.google/oauth-callback"


def test_generic_oauth_refuses_to_advertise_without_admin_registration(monkeypatch):
    monkeypatch.delenv("MCP_VERSUS_OAUTH_GENERIC_ENABLED", raising=False)

    payload = McpVersusOAuthConnectorService().build_config("other")

    assert payload["available"] is False
    assert payload["server_name"] == "mcp-versus"
    assert "redirect URI" in payload["message"]


def test_claude_is_not_advertised_until_dcr_policy_is_ready(monkeypatch):
    monkeypatch.setenv("MCP_VERSUS_OAUTH_CLAUDE_ENABLED", "1")
    monkeypatch.delenv("MCP_VERSUS_OAUTH_CLAUDE_DCR_READY", raising=False)

    payload = McpVersusOAuthConnectorService().build_config("claude")

    assert payload == {
        "available": False,
        "runtime": "claude",
        "readiness": "blocked",
        "message": "Integração OAuth do Claude em preparação pela Versus. Não configure o conector ainda.",
        "support_code": "claude_dcr_not_ready",
    }
