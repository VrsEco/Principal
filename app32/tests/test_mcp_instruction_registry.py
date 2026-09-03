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
    intake = payload["data"]["process_modeling_intake_contract"]
    assert intake["schema"] == "process_modeling_intake.v1"
    assert intake["required_payload"]["source"]["type"] == "audio|text|legacy_document|mixed"
    assert "transcript" in intake["required_payload"]
    assert "statements" in intake["required_payload"]
    assert any("não publicar" in item.lower() for item in intake["cli_pipeline"])



def test_instruction_registry_exposes_structuring_journey_guide_only_to_squad_cliente():
    mcp = _FakeMCP()
    register_instruction_registry_tools(mcp)

    client_payload = mcp.registered["resolve_app32_instruction_bundle_tool"](
        runtime_profile="squad_cliente",
        company_id=31,
    )
    guide = client_payload["data"]["journey_guide"]

    assert guide["version"] == "structuring-journey-v2.1"
    assert guide["entry_state"] == "collecting_evidence"
    assert [item["key"] for item in guide["states"]] == [
        "collecting_evidence",
        "awaiting_client_validation",
        "awaiting_versus_validation",
        "awaiting_engineering_validation",
        "awaiting_consultant_decision",
        "approved_for_execution",
        "executed_verified",
        "blocked",
    ]
    action_policy = {item["action"]: item["autonomy"] for item in guide["action_policy"]}
    assert action_policy["collect_human_evidence"] == "must"
    assert action_policy["classify_assisted_analysis"] == "must"
    assert action_policy["register_canonical_data"] == "cannot"
    assert action_policy["execute_authorized_mutation"] == "gated"
    assert "consultive_resolve_protocol" in guide["read_tool_sequence"]
    assert all(
        not tool.startswith(("consultive_register_", "consultive_upsert_"))
        for tool in guide["read_tool_sequence"]
    )

    versus_payload = mcp.registered["resolve_app32_instruction_bundle_tool"](
        runtime_profile="squad_versus",
        company_id=31,
    )
    assert versus_payload["data"]["journey_guide"] is None
    assert versus_payload["data"]["process_modeling_intake_contract"]["schema"] == "process_modeling_intake.v1"


def test_instruction_registry_supports_engineering_runtime():
    mcp = _FakeMCP()
    register_instruction_registry_tools(mcp)

    payload = mcp.registered["resolve_app32_instruction_bundle_tool"](runtime_profile="engineering")

    assert payload["success"] is True
    assert payload["data"]["runtime_profile"] == "engineering"
    assert payload["data"]["surface"] == "ops"
    assert payload["data"]["process_modeling_intake_contract"] is None


def test_instruction_registry_rejects_unknown_runtime():
    mcp = _FakeMCP()
    register_instruction_registry_tools(mcp)

    payload = mcp.registered["resolve_app32_instruction_bundle_tool"](runtime_profile="foo")

    assert payload["success"] is False
    assert payload["error"]["code"] == "instruction_bundle_invalid_request"
