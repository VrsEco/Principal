from services.mcp_versus_oauth_connector_service import McpVersusOAuthConnectorService


def test_mcp_versus_is_the_fixed_public_connection_name(monkeypatch):
    monkeypatch.setenv("MCP_VERSUS_OAUTH_CODEX_ENABLED", "1")
    monkeypatch.setenv("MCP_VERSUS_OAUTH_CODEX_CLIENT_ID", "mcp-versus-codex")

    payload = McpVersusOAuthConnectorService().build_config("codex")

    assert payload["server_name"] == "mcp-versus"
    assert payload["client_id"] == "mcp-versus-codex"
    assert payload["add_command"].startswith("codex mcp add mcp-versus ")
    assert "company_id" not in payload


def test_claude_configuration_uses_dcr_without_exposing_a_static_client_id(monkeypatch):
    monkeypatch.setenv("MCP_VERSUS_OAUTH_CLAUDE_ENABLED", "1")
    monkeypatch.setenv("MCP_VERSUS_OAUTH_CLAUDE_CLIENT_ID", "mcp-versus-claude")

    payload = McpVersusOAuthConnectorService().build_config("claude")

    assert payload["available"] is True
    assert payload["server_name"] == "mcp-versus"
    assert payload["registration_mode"] == "dynamic"
    assert "client_id" not in payload
    assert payload["redirect_uri"] == "https://claude.ai/api/mcp/auth_callback"
    assert not any("token" in str(key).lower() for key in payload)
    assert any("Não informe client ID nem token manualmente." in item for item in payload["instructions"])
    assert any("homologação deste cliente é independente" in item for item in payload["instructions"])


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
