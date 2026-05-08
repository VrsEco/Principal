from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[1]


def test_profile_template_keeps_selected_company_on_token_actions():
    template = (_REPO_ROOT / "templates" / "auth" / "profile.html").read_text(encoding="utf-8")

    assert "function buildMcpTokenPayload()" in template
    assert "return buildMcpConfigPayload();" in template
    assert "function injectLatestTokenIntoConfig(config)" in template
    assert "TOKEN_GERADO_APENAS_NA_RENOVACAO" in template
