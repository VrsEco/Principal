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
    assert payload["login_command"] == "codex mcp login app32-pilot"
    assert "company_id" not in payload
    assert "token" not in payload
