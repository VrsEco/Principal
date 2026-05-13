from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[1]


def test_ai_mcp_console_template_declares_expected_sections():
    template = (_REPO_ROOT / "templates" / "modules" / "operations" / "ai_mcp_console.html").read_text(encoding="utf-8")

    for expected in [
        "Console operacional",
        "API / MCP",
        "aiMcpConsolePage",
        "aiMcpConsoleSearch",
        "data-console-tab",
        "data-console-go-tab",
        "Catálogo",
        "Wizard de uso e configuração",
        "Perfis & Permissões",
        "Onboarding & Cadastros",
        "Ativar Sapiens em outro cliente",
        "Leitura automática do catálogo MCP",
        "Ativar Sapiens",
        "Configuração técnica",
        "Release & Freeze",
        "Dashboard & Readiness",
        "Governança",
        "Contexto operacional",
        "aiMcpRuntimeContextSummary",
        "aiMcpBootstrapContextRequired",
        "aiMcpBootstrapContextResolved",
        "aiMcpBootstrapContextResolution",
        "aiMcpBootstrapContextSummary",
    ]:
        assert expected in template


def test_ai_mcp_console_assets_declare_interaction_contract():
    css = (_REPO_ROOT / "static" / "css" / "ai_mcp_console.css").read_text(encoding="utf-8")
    script = (_REPO_ROOT / "static" / "js" / "ai_mcp_console.js").read_text(encoding="utf-8")

    assert ".ai-mcp-console-page" in css
    assert ".ai-mcp-connection-generator" in css
    assert ".ai-mcp-bootstrap-card__content" in css
    assert ".ai-mcp-context-grid" in css
    assert ".ai-mcp-context-card" in css
    assert ".ai-mcp-context-list" in css
    assert ".ai-mcp-tab" in css
    assert ".ai-mcp-panel" in css
    assert "aiMcpConsolePage" in script
    assert "aiMcpConnectionGenerator" in script
    assert "aiMcpDocumentationBootstrap" in script
    assert "aiMcpRuntimeContextSummary" in script
    assert "renderRuntimeContext" in script
    assert "renderBootstrapContext" in script
    assert "autoBootstrapDocumentationCatalog" in script
    assert "Comando Ativar Sapiens pronto para copiar" in script
    assert "aiMcpConsoleSearch" in script
    assert "data-console-tab" in script
    assert "applySearch" in script
    assert "normalize(" in script
