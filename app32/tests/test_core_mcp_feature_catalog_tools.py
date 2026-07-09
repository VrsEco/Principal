from src.core.mcp_feature_catalog_tools import register_feature_catalog_tools


class _FakeMCP:
    def __init__(self):
        self.registered = {}

    def tool(self, *args, **kwargs):
        def decorator(func):
            self.registered[kwargs.get("name") or func.__name__] = func
            return func

        if args and callable(args[0]):
            return decorator(args[0])
        return decorator


def test_feature_catalog_tools_bootstrap_and_filter(monkeypatch):
    monkeypatch.setenv("APP32_MCP_SURFACE", "user")
    monkeypatch.setenv("APP32_MCP_COMPANY_ID", "31")
    monkeypatch.setenv("APP32_MCP_USER_ID", "7")
    monkeypatch.setenv("APP32_MCP_FALLBACK_ROLE", "colaborador")

    mcp = _FakeMCP()
    register_feature_catalog_tools(mcp)

    payload = mcp.registered["bootstrap_session_context"]()
    assert payload["success"] is True
    assert payload["data"]["company_id"] == 31
    assert payload["data"]["surface"] == "user"
    assert {
        "rotina_tarefas",
        "processos_acompanhamento",
    }.issubset({feature["id"] for feature in payload["data"]["features"]})

    filtered = mcp.registered["list_feature_catalog"](domain="routine")
    assert filtered["success"] is True
    assert "rotina_tarefas" in [feature["id"] for feature in filtered["data"]["features"]]


def test_feature_catalog_tools_enforce_company_context_and_surface(monkeypatch):
    monkeypatch.delenv("APP32_MCP_COMPANY_ID", raising=False)
    monkeypatch.setenv("APP32_MCP_SURFACE", "user")

    mcp = _FakeMCP()
    register_feature_catalog_tools(mcp)

    bootstrap = mcp.registered["bootstrap_session_context"]()
    assert bootstrap["success"] is True
    assert bootstrap["data"]["company_id"] is None
    assert bootstrap["data"]["current_context"]["required"] == []

    monkeypatch.setenv("APP32_MCP_COMPANY_ID", "31")
    forbidden = mcp.registered["get_feature_guide"]("financeiro_fluxo_caixa")
    assert forbidden["success"] is False
    assert forbidden["error"]["code"] == "mcp_feature_catalog_forbidden_surface"
