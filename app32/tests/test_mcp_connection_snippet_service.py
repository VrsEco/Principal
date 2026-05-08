import pytest

from services.mcp_connection_snippet_service import MCPConnectionSnippetService


def test_build_prompt_includes_manual_or_automatic_question():
    content = MCPConnectionSnippetService.build_prompt(
        {
            "name": "Sapiens User",
            "default_company": "Sem empresa padrão",
            "url": "https://app.gestaoversus.com.br/mcp/user",
            "auth_type": "bearer",
            "token": "token-123",
        }
    )

    assert "configuração automática" in content
    assert "configuração manual" in content
    assert "https://app.gestaoversus.com.br/mcp/user" in content


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
