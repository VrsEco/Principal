from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[1]


def test_profile_template_supports_activation_and_technical_mcp_outputs():
    template = (_REPO_ROOT / "templates" / "auth" / "profile.html").read_text(encoding="utf-8")

    assert "Copiar comando de instalação" in template
    assert "Ver configuração técnica" in template
    assert "Ver harness" in template
    assert "Executar smoke guiado" in template
    assert "Onboarding por runtime e squad" in template
    assert "function buildMcpTokenPayload()" in template
    assert "return buildMcpConfigPayload();" in template
    assert "function injectLatestTokenIntoConfig(config)" in template
    assert "const resolvedData = injectLatestTokenIntoConfig(data.data);" in template
    assert "const resolvedConfig = injectLatestTokenIntoConfig(config);" in template
    assert "install_command: replacePlaceholder(config.install_command)" in template
    assert "resolvedConfig.copy_install_command_text || resolvedConfig.install_command" in template
    assert "activation_prompt" in template
    assert "technical_config_text" in template
    assert "buildMcpConfig('activation'" in template
    assert "buildMcpConfig('technical'" in template
    assert "buildMcpConfig('harness'" in template
    assert "buildMcpConfig('smoke'" in template
