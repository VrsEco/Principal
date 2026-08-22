from pathlib import Path


def test_claude_desktop_windows_installer_uses_custom_stdio_proxy():
    script_path = Path(r"C:\GestaoVersus\app32\app32\scripts\installers\install-sapiens-claude-desktop-windows.ps1")
    content = script_path.read_text(encoding="utf-8")

    assert "sapiens-proxy.js" in content
    assert "claude_desktop_config.json" in content
    assert "SAPIENS_MCP_TOKEN" in content
    assert "SAPIENS_MCP_URL" in content
    assert "mcp-remote" not in content
    assert 'replace(/\\r\\n/g, "\\n")' in content
    assert "reader.cancel()" in content
    assert "stdinDone" in content
    assert 'const VERSION = "1.1.0"' in content
    assert "response.status === 202" in content
    assert "message.id === undefined" in content
    assert 'RETRYABLE_METHODS = new Set(["initialize", "tools/list", "prompts/list", "resources/list"])' in content
    assert "const maxAttempts = RETRYABLE_METHODS.has(message.method) ? 3 : 1" in content
    assert 'SAPIENS_MCP_TIMEOUT_MS = "60000"' in content
    assert "Invoke-ProxySmoke" in content
    assert '$ProxyVersion = "1.1.0"' in content
    assert "protocolVersion\":\"2025-03-26" in content
    assert "WaitForExit(190000)" in content
    assert "TOKEN_GERADO_APENAS_NA_RENOVACAO" in content
    assert "BearerToken ainda está como placeholder" in content


def test_claude_desktop_windows_installer_preserves_existing_config():
    script_path = Path(r"C:\GestaoVersus\app32\app32\scripts\installers\install-sapiens-claude-desktop-windows.ps1")
    content = script_path.read_text(encoding="utf-8")

    assert "Read-JsonConfig" in content
    assert "ConvertTo-HashtableCompat" not in content
    assert "Set-McpServer" in content
    assert "PSObject.Properties[\"mcpServers\"]" in content
    assert "arrays vazios como `{}`" in content
    assert "Backup-IfExists" in content
    assert "mcpServers" in content
    assert "ConvertTo-Json -Depth 40" in content
