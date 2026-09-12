from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[1]


def test_profile_template_supports_simple_runtime_installer_flow():
    template = (_REPO_ROOT / "templates" / "auth" / "profile.html").read_text(encoding="utf-8")

    assert "Dados e comunicação" in template
    assert "Instalar Squad" in template
    assert "Segurança" in template
    assert "profile-tab-panel is-active" in template
    assert "profileForm" in template
    assert "changePasswordForm" in template
    assert "Instalação em uma página" in template
    assert "Escolha da ferramenta" in template
    assert "data-choice-value=\"claude\"" in template
    assert "data-choice-value=\"antigravity\"" in template
    assert "data-choice-value=\"codex\"" in template
    assert "data-choice-value=\"other\"" in template
    assert "Genérica" in template
    assert "Escolha o Squad" in template
    assert "data-choice-value=\"squad_cliente\"" in template
    assert "data-choice-value=\"squad_versus\"" in template
    assert "data-choice-value=\"engineering\"" in template
    assert "Criar token" in template
    assert "Renovar" in template
    assert "Revogar" in template
    assert "Usuário Normal" in template
    assert "Usuário Avançado" in template
    assert "Instalação Técnica" in template
    assert "Copiar Comando" in template
    assert "id=\"mcpConnectorCard\"" in template
    assert "Conectar Claude" in template
    assert "OAuth remoto para Claude ainda não foi homologado" in template
    assert "function renderMcpConnectorForRuntime(config = null)" in template
    assert "if (selectedMcpRuntime === 'codex') await loadOAuthCodexConfig(false);" in template
    assert "function buildMcpTokenPayload()" in template
    assert "return buildMcpConfigPayload();" in template
    assert "function outputForMode(config, mode)" in template
    assert "const resolvedConfig = config;" in template
    assert "cli_install_text" in template
    assert "powershell_install_command" in template
    assert "config.copy_install_command_text || config.install_command" in template
    assert "activation_prompt" in template
    assert "technical_config_text" in template
    assert "selectedInstallMode = 'prompt'" in template
    assert "mode === 'powershell'" in template
    assert "mode === 'technical'" in template
    assert "overflow-wrap: anywhere" in template
    assert "activateProfileTab('profile-mcp-panel')" in template
