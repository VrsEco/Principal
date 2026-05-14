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

    assert "ative o Sapiens Consultor" in content
    assert "Família canônica: Squad Versus" in content
    assert "sapiens consultor on" in content
    assert "Surface alvo: admin" in content
    assert "list_admin_app32_capabilities" in content
    assert "https://app.gestaoversus.com.br/mcp/admin" in content


def test_build_prompt_supports_squad_cliente_profile():
    content = MCPConnectionSnippetService.build_prompt(
        {
            "profile": "squad_cliente",
            "default_company": "Cliente XP",
            "auth_type": "bearer",
            "token": "token-cli",
        }
    )

    assert "ative o Sapiens Cliente" in content
    assert "Família canônica: Squad Cliente" in content
    assert "sapiens cliente on" in content
    assert "Surface alvo: user" in content
    assert "Harness inicial: Harness Coordenador do Squad Cliente" in content
    assert "describe_app32_squad_runtime_tool" in content
    assert "list_user_app32_capabilities" in content
    assert "describe_app32_profile_contracts_tool" in content
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


def test_build_raw_config_includes_runtime_profile_metadata():
    content = MCPConnectionSnippetService.build_raw_config(
        {
            "profile": "squad_versus",
            "auth_type": "bearer",
            "token": "token-123",
        }
    )

    assert '"profile": "squad_versus"' in content
    assert '"profile_label": "Squad Versus"' in content
    assert '"experience_label": "Sapiens Consultor"' in content
    assert '"surface": "admin"' in content


def test_build_raw_config_includes_harness_metadata_for_squad_cliente():
    content = MCPConnectionSnippetService.build_raw_config(
        {
            "profile": "squad_cliente",
            "auth_type": "bearer",
            "token": "token-123",
        }
    )

    assert '"harness_key": "harness_coordenador_cliente_v1"' in content
    assert '"harness_label": "Harness Coordenador do Squad Cliente"' in content


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


def test_build_prompt_supports_engineering_profile():
    content = MCPConnectionSnippetService.build_prompt(
        {
            "profile": "engineering",
            "default_company": "App32",
            "auth_type": "bearer",
            "token": "token-eng",
        }
    )

    assert "ative o Sapiens Engenharia" in content
    assert "Família canônica: Squad de Engenharia" in content
    assert "sapiens engenharia on" in content
    assert "Surface alvo: ops" in content
    assert "Harness inicial: Harness Coordenador do Squad de Engenharia" in content
    assert "list_ops_app32_capabilities" in content
    assert "https://app.gestaoversus.com.br/mcp/ops" in content


def test_build_raw_config_includes_harness_metadata_for_engineering():
    content = MCPConnectionSnippetService.build_raw_config(
        {
            "profile": "engineering",
            "auth_type": "bearer",
            "token": "token-123",
        }
    )

    assert '"profile": "engineering"' in content
    assert '"surface": "ops"' in content
    assert '"harness_key": "harness_coordenador_engenharia_v1"' in content
