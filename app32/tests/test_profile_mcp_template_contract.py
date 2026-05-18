from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[1]


def test_profile_template_supports_simple_runtime_installer_flow():
    template = (_REPO_ROOT / "templates" / "auth" / "profile.html").read_text(encoding="utf-8")

    assert "Instalação via CLI" in template
    assert "Instalação via PowerShell" in template
    assert "Ver modo técnico" in template
    assert "Instalar Sapiens no seu CLI" in template
    assert "o instalador sempre baixa o script oficial online" in template.lower()
    assert "Ver detalhes técnicos desta instalação" in template
    assert "Ver contexto avançado do squad" in template
    assert "Claude Code / aba Code do Desktop" in template
    assert "A aba <strong>Chat</strong> / Connectors usa outra superfície" in template
    assert "function buildMcpTokenPayload()" in template
    assert "return buildMcpConfigPayload();" in template
    assert "function injectLatestTokenIntoConfig(config)" in template
    assert "const resolvedData = injectLatestTokenIntoConfig(data.data);" in template
    assert "const resolvedConfig = injectLatestTokenIntoConfig(config);" in template
    assert "install_command: replacePlaceholder(config.install_command)" in template
    assert "cli_install_text" in template
    assert "powershell_install_command" in template
    assert "resolvedConfig.copy_install_command_text || resolvedConfig.install_command" in template
    assert "activation_prompt" in template
    assert "technical_config_text" in template
    assert "buildMcpConfig('activation'" in template
    assert "buildMcpConfig('cli'" in template
    assert "buildMcpConfig('technical'" in template
