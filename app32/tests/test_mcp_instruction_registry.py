from src.core.mcp_instruction_registry_tools import register_instruction_registry_tools


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


def test_instruction_registry_describe_returns_manifest_with_json_and_yaml_models():
    mcp = _FakeMCP()
    register_instruction_registry_tools(mcp)

    payload = mcp.registered["describe_app32_instruction_registry_tool"]()

    assert payload["success"] is True
    assert payload["meta"]["operation"] == "instruction_registry.describe"
    assert payload["data"]["version"] == "app32.mcp.instructions.v1"
    assert payload["data"]["bundle_template_json"]["runtime_profile"] == "squad_cliente"
    assert "runtime_profile: squad_cliente" in payload["data"]["bundle_template_yaml"]


def test_instruction_registry_resolves_squad_cliente_bundle():
    mcp = _FakeMCP()
    register_instruction_registry_tools(mcp)

    payload = mcp.registered["resolve_app32_instruction_bundle_tool"](
        runtime_profile="squad_cliente",
        harness_key="harness_coordenador_cliente_v1",
        company_id=31,
    )

    assert payload["success"] is True
    assert payload["meta"]["operation"] == "instruction_bundle.resolve"
    assert payload["data"]["runtime_profile"] == "squad_cliente"
    assert payload["data"]["agent_key"] == "SC-COORD"
    assert payload["data"]["company_id"] == 31
    assert payload["data"]["startup_sequence"][0] == "resolve_app32_instruction_bundle_tool"
    assert payload["data"]["checksum"]
    assert payload["data"]["invalidation_token"]
    assert payload["data"]["cache_key"].startswith("instruction-registry:squad_cliente")
    assert any(item["doc_class"] == "spec" for item in payload["data"]["doc_refs"])


def test_instruction_registry_supports_engineering_runtime():
    mcp = _FakeMCP()
    register_instruction_registry_tools(mcp)

    payload = mcp.registered["resolve_app32_instruction_bundle_tool"](runtime_profile="engineering")

    assert payload["success"] is True
    assert payload["data"]["runtime_profile"] == "engineering"
    assert payload["data"]["surface"] == "ops"


def test_instruction_registry_rejects_unknown_runtime():
    mcp = _FakeMCP()
    register_instruction_registry_tools(mcp)

    payload = mcp.registered["resolve_app32_instruction_bundle_tool"](runtime_profile="foo")

    assert payload["success"] is False
    assert payload["error"]["code"] == "instruction_bundle_invalid_request"
