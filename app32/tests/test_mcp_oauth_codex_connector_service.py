from services.mcp_oauth_codex_connector_service import McpOAuthCodexConnectorService


def test_connector_is_closed_by_default(monkeypatch):
    monkeypatch.delenv("APP32_MCP_OAUTH_CODEX_CONNECTOR_ENABLED", raising=False)

    payload = McpOAuthCodexConnectorService().build_config()

    assert payload == {
        "available": False,
        "message": "Conexão OAuth do Codex ainda não está liberada para esta coorte.",
    }


def test_connector_builds_public_codex_commands_without_tenant_or_token(monkeypatch):
    monkeypatch.setenv("APP32_MCP_OAUTH_CODEX_CONNECTOR_ENABLED", "1")
    monkeypatch.setenv("APP32_MCP_OAUTH_CODEX_CLIENT_ID", "app32-mcp-codex")
    monkeypatch.setenv("APP32_PUBLIC_BASE_URL", "https://app.example.test/")

    payload = McpOAuthCodexConnectorService().build_config()

    assert payload["available"] is True
    assert payload["mcp_url"] == "https://app.example.test/mcp/pilot/user/"
    assert "--oauth-client-id app32-mcp-codex" in payload["add_command"]
    assert payload["login_command"] == "codex mcp login mcp-versus"
    assert "company_id" not in payload
    assert "token" not in payload


def test_connector_accepts_explicit_connection_name_without_changing_client_id(monkeypatch):
    monkeypatch.setenv("APP32_MCP_OAUTH_CODEX_CONNECTOR_ENABLED", "1")
    monkeypatch.setenv("APP32_MCP_OAUTH_CODEX_CLIENT_ID", "app32-mcp-codex")
    monkeypatch.setenv("APP32_MCP_OAUTH_CODEX_SERVER_NAME", "mcp-versus")

    payload = McpOAuthCodexConnectorService().build_config()

    assert payload["server_name"] == "mcp-versus"
    assert payload["client_id"] == "app32-mcp-codex"
    assert payload["add_command"].startswith("codex mcp add mcp-versus ")
