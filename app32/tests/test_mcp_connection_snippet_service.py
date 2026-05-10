import pytest

from services.mcp_connection_snippet_service import MCPConnectionSnippetService


def test_build_prompt_includes_activation_and_fallback_pattern():
    content = MCPConnectionSnippetService.build_prompt(
        {
            "name": "Sapiens User",
            "default_company": "Sem empresa padrão",
            "url": "https://app.gestaoversus.com.br/mcp/user",
            "auth_type": "bearer",
            "token": "token-123",
        }
    )

    assert "ative o Sapiens" in content
    assert "◆ SAPIENS · Gestão Versus ● ativo" in content
    assert "Este cliente não suporta ativação automática do Sapiens." in content
    assert "https://app.gestaoversus.com.br/mcp/user" in content


def test_build_prompt_supports_squad_versus_profile():
    content = MCPConnectionSnippetService.build_prompt(
        {
            "profile": "squad_versus",
            "default_company": "Versus",
            "auth_type": "bearer",
            "token": "token-abc",
        }
    )

    assert "ative o Squad Versus" in content
    assert "Surface alvo: admin" in content
    assert "list_app32_capabilities" in content
    assert "https://app.gestaoversus.com.br/mcp/admin" in content


def test_build_raw_config_includes_bearer_header():
    content = MCPConnectionSnippetService.build_raw_config(
        {
            "name": "Sapiens User",
            "default_company": "Sem empresa padrão",
            "url": "https://app.gestaoversus.com.br/mcp/user",
            "auth_type": "bearer",
            "token": "token-123",
        }
    )

    assert '"transport": "http"' in content
    assert '"Authorization": "Bearer token-123"' in content


def test_build_raw_config_includes_runtime_profile_metadata():
    content = MCPConnectionSnippetService.build_raw_config(
        {
            "profile": "squad_versus",
            "auth_type": "bearer",
            "token": "token-123",
        }
    )

    assert '"profile": "squad_versus"' in content
    assert '"surface": "admin"' in content


def test_build_prompt_rejects_invalid_url():
    with pytest.raises(ValueError, match="URL inválida"):
        MCPConnectionSnippetService.build_prompt(
            {
                "name": "Sapiens User",
                "default_company": "Sem empresa padrão",
                "url": "ftp://app.gestaoversus.com.br/mcp/user",
                "auth_type": "bearer",
                "token": "token-123",
            }
        )
