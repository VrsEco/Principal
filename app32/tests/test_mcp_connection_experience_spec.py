from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_mcp_connection_experience_spec_contract():
    spec = (ROOT / "docs" / "spec" / "experiencia_conexao_app32_cli_ia_mcp_api_v1.md").read_text(encoding="utf-8")

    assert "Connection Profile" in spec
    assert "`/profile`" in spec
    assert "`/api-mcp`" in spec
    assert "`/channels`" in spec
    assert "console técnico" in spec.lower()
    assert "Bearer Token MVP" in spec
    assert "OAuth" in spec
    assert "company_id" in spec
    assert "Codex" in spec
    assert "Claude" in spec
    assert "Gemini/Antigravity" in spec
    assert "VS Code/Copilot" in spec


def test_mcp_connection_experience_paper_links_spec():
    paper = (ROOT / "docs" / "papers" / "paper_comunicacao_app32_cli_ia_mcp_api_estagio_zero_v0.md").read_text(encoding="utf-8")

    assert "MCP-02" in paper
    assert "experiencia_conexao_app32_cli_ia_mcp_api_v1.md" in paper
    assert "Connection Profile" in paper


def test_external_ai_onboarding_manual_links_mcp02_journey():
    manual = (ROOT / "docs" / "governance" / "external_ai_mcp_onboarding_manual.md").read_text(encoding="utf-8")

    assert "Complemento MCP-02" in manual
    assert "experiencia_conexao_app32_cli_ia_mcp_api_v1.md" in manual
    assert "`/profile`: conexão pessoal CLI/IA" in manual
