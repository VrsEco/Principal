from src.core.mcp_external_llm_factory_tools import register_external_llm_factory_tools
from src.core.mcp_sapiens_factory_tools import register_sapiens_factory_tools


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


def test_register_sapiens_factory_tools():
    mcp = _FakeMCP()

    register_sapiens_factory_tools(mcp)

    describe = mcp.registered["describe_app32_sapiens_factory_tool"]()
    assert describe["success"] is True
    assert describe["data"]["surface_key"] == "factory"

    assess = mcp.registered["assess_app32_change_request_tool"](
        request_text="Precisamos evoluir o workflow xyz para melhorar os resultados.",
        execution_mode="plan",
    )
    assert assess["success"] is True
    assert assess["data"]["request"]["change_type"] in {"alter", "diagnose", "fix"}

    not_found = mcp.registered["trace_app32_capability_dependencies_tool"]("nao_existe")
    assert not_found["success"] is False


def test_register_external_llm_factory_tools():
    mcp = _FakeMCP()

    register_external_llm_factory_tools(mcp)

    describe = mcp.registered["describe_app32_external_llm_factory_surface_tool"]()
    assert describe["success"] is True
    assert describe["data"]["surface_key"] == "external_factory"

    evaluation = mcp.registered["evaluate_app32_external_llm_factory_session_tool"](
        client_name="Codex CLI",
        provider="OpenAI",
        use_case="Operar a factory assistida via MCP",
    )
    assert evaluation["success"] is True
    assert evaluation["data"]["allowed"] is True
