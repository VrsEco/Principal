"""O conector mcp-versus entrega o contrato do Squad Cliente no initialize."""
from src.core import mcp_surface_registry as registry


def _initialize_instructions(server) -> str | None:
    # É o que o cliente MCP recebe no initialize e injeta no contexto do agente.
    return server._mcp_server.create_initialization_options().instructions


def test_unified_server_publishes_squad_cliente_contract():
    text = _initialize_instructions(registry.build_oauth_unified_mcp_server()) or ""
    assert "Squad Cliente on" in text
    assert "list_my_companies" in text
    assert "company_id" in text
    assert "list_user_app32_capabilities" in text
    assert "RBAC" in text


def test_instructions_stay_within_context_budget():
    words = len(registry.UNIFIED_SERVER_INSTRUCTIONS.split())
    assert words <= 220, f"{words} palavras excedem o orçamento do contrato remoto"


def test_instructions_only_reference_published_tools():
    import asyncio

    server = registry.build_oauth_unified_mcp_server()
    published = {tool.name for tool in asyncio.run(server.list_tools())}
    assert "list_my_companies" in published
    assert "list_user_app32_capabilities" in published


def test_other_surfaces_do_not_publish_instructions():
    assert not _initialize_instructions(registry.build_user_mcp_server())
