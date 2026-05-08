from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[1]


def test_profile_template_supports_activation_and_technical_mcp_outputs():
    template = (_REPO_ROOT / "templates" / "auth" / "profile.html").read_text(encoding="utf-8")

    assert "Ativar Sapiens" in template
    assert "Configuração técnica" in template
    assert "function buildMcpTokenPayload()" in template
    assert "return buildMcpConfigPayload();" in template
    assert "function injectLatestTokenIntoConfig(config)" in template
    assert "activation_prompt" in template
    assert "technical_config_text" in template
    assert "buildMcpConfig('activation'" in template
    assert "buildMcpConfig('technical'" in template
