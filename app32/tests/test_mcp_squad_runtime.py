from src.core.mcp_squad_runtime_tools import register_squad_runtime_tools


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


def test_squad_runtime_tool_returns_official_squad_cliente_bootstrap():
    mcp = _FakeMCP()
    register_squad_runtime_tools(mcp)
    tool = mcp.registered["describe_app32_squad_runtime_tool"]

    payload = tool(runtime_profile="squad_cliente")

    assert payload["success"] is True
    assert payload["data"]["runtime_profile"] == "squad_cliente"
    assert payload["data"]["official_phase_label"] == "Fase 1 oficial"
    assert payload["data"]["entry_agent"]["key"] == "SC-COORD"
    assert payload["data"]["startup_tools"][0] == "describe_app32_squad_runtime_tool"
    assert [item["key"] for item in payload["data"]["agents"]] == [
        "SC-COORD",
        "SC-COM",
        "SC-OPS",
        "SC-ADM",
    ]
    assert [item["key"] for item in payload["data"]["harnesses"]] == [
        "harness_coordenador_cliente_v1",
        "harness_comercial_cliente_v1",
        "harness_operacional_cliente_v1",
        "harness_admfin_cliente_v1",
    ]


def test_squad_runtime_tool_supports_generic_runtime_fallback():
    mcp = _FakeMCP()
    register_squad_runtime_tools(mcp)
    tool = mcp.registered["describe_app32_squad_runtime_tool"]

    payload = tool(runtime_profile="engineering")

    assert payload["success"] is True
    assert payload["data"]["runtime_profile"] == "engineering"
    assert payload["data"]["default_harness_key"] == "harness_coordenador_engenharia_v1"


def test_squad_runtime_tool_rejects_unknown_runtime():
    mcp = _FakeMCP()
    register_squad_runtime_tools(mcp)
    tool = mcp.registered["describe_app32_squad_runtime_tool"]

    payload = tool(runtime_profile="foo")

    assert payload["success"] is False
    assert payload["error"]["code"] == "squad_runtime_not_found"
