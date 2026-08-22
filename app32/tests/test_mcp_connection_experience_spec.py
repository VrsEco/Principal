from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_mcp_connection_experience_spec_contract():
    spec = (ROOT / "docs" / "spec" / "experiencia_conexao_app32_cli_ia_mcp_api_v1.md").read_text(encoding="utf-8")

    assert "Connection Profile" in spec
    assert "tela única de Conexões" in spec
    assert "`/channels`" in spec
    assert "`/profile`" in spec
    assert "modo detalhado" in spec
    assert "`/api-mcp`" in spec
    assert "console técnico" in spec.lower()
    assert "Bearer Token MVP" in spec
    assert "OAuth" in spec
    assert "company_id" in spec
    assert "Codex" in spec
    assert "Claude" in spec
    assert "Gemini/Antigravity" in spec
    assert "VS Code/Copilot" in spec
    assert "MCP-05" in spec
    assert "runbook_mcp_runtime_resiliencia_v1.md" in spec


def test_mcp_connection_experience_paper_links_spec():
    paper = (ROOT / "docs" / "papers" / "paper_comunicacao_app32_cli_ia_mcp_api_estagio_zero_v0.md").read_text(encoding="utf-8")

    assert "MCP-02" in paper
    assert "experiencia_conexao_app32_cli_ia_mcp_api_v1.md" in paper
    assert "Connection Profile" in paper
    assert "tela única de Conexões" in paper
    assert "MCP-05" in paper
    assert "monitor_mcp_http.sh" in paper


def test_mcp_runtime_resilience_runbook_contract():
    runbook = (ROOT / "docs" / "runbooks" / "runbook_mcp_runtime_resiliencia_v1.md").read_text(encoding="utf-8")

    assert "scripts/manage_mcp_http.sh" in runbook
    assert "scripts/monitor_mcp_http.sh" in runbook
    assert "/api/integrations/mcp-runtime/repair" in runbook
    assert "streamable-http" in runbook


def test_external_ai_onboarding_manual_links_mcp02_journey():
    manual = (ROOT / "docs" / "governance" / "external_ai_mcp_onboarding_manual.md").read_text(encoding="utf-8")

    assert "Complemento MCP-02" in manual
    assert "experiencia_conexao_app32_cli_ia_mcp_api_v1.md" in manual
    assert "`/channels`: tela única de Conexões" in manual
    assert "`/profile`: modo detalhado/fallback" in manual


def test_connections_page_contains_mcp_unified_entrypoint():
    template = (ROOT / "templates" / "integrations_admin.html").read_text(encoding="utf-8")

    assert "Conexões | Versus" in template
    assert "CLI/IA via MCP" in template
    assert "section-mcp" in template
    assert "connectionsMcpRuntime" in template
    assert "connectionsMcpSquad" in template
    assert "connectionsMcpCompany" in template
    assert "/profile/mcp-token/status" in template
    assert "/profile/mcp-token/config" in template
    assert "/mcp/healthz" in template
    assert "Reparar runtime MCP" in template
    assert "/api/integrations/mcp-runtime/repair" in template
    assert "repairConnectionsMcpRuntime" in template
    assert "Token MCP obrigatório para concluir a instalação." in template
    assert "injectConnectionsToken" not in template


def test_profile_mcp_page_blocks_placeholder_command_copy():
    template = (ROOT / "templates" / "auth" / "profile.html").read_text(encoding="utf-8")

    assert "Token MCP obrigatório para concluir a instalação." in template
    assert "Por segurança, o APP32 não exibe comando executável com token placeholder." in template
    assert "token_required" in template
    assert "const needsToken = Boolean(config.token_required);" in template
    assert "injectLatestTokenIntoConfig" not in template
    assert "return resolvedData;" not in template
    token_action = template.split("async function runMcpTokenAction", 1)[1].split("function copyText", 1)[0]
    assert "await buildMcpConfig(false).catch(() => {});" not in token_action


def test_connections_mcp_page_never_replaces_encoded_command_token_in_browser():
    template = (ROOT / "templates" / "integrations_admin.html").read_text(encoding="utf-8")

    assert "injectConnectionsToken" not in template
    assert "if (resolved.token_required)" in template


