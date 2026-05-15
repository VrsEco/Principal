from pathlib import Path


def test_claude_slash_installer_enforces_official_bootstrap_and_alias():
    script_path = Path(r"C:\GestaoVersus\app32\app32\scripts\installers\install-claude-sapiens-slash-commands.ps1")
    content = script_path.read_text(encoding="utf-8")

    assert "A conexão MCP do Sapiens Cliente não está disponível nesta sessão." in content
    assert "describe_app32_domain_playbooks_tool" in content
    assert "Nunca mande o usuário digitar `sapiens on` como texto livre." in content
    assert '-FileName "sapiens.md"' in content
    assert "Nunca trate este comando como skill genérica solta." in content
