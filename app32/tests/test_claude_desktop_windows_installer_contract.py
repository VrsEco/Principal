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
    assert "Invoke-ProxySmoke" in content
    assert "protocolVersion\":\"2024-11-05" in content


def test_claude_desktop_windows_installer_preserves_existing_config():
    script_path = Path(r"C:\GestaoVersus\app32\app32\scripts\installers\install-sapiens-claude-desktop-windows.ps1")
    content = script_path.read_text(encoding="utf-8")

    assert "Read-JsonConfig" in content
    assert "ConvertTo-HashtableCompat" in content
    assert "Backup-IfExists" in content
    assert "mcpServers" in content
    assert "ConvertTo-Json -Depth 40" in content
