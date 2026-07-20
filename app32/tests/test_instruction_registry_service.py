from services.instruction_registry_service import InstructionRegistryService


def test_instruction_registry_service_resolves_squad_versus_bundle_without_db():
    payload = InstructionRegistryService.resolve_bundle(runtime_profile="squad_versus", channel="stable")

    assert payload["runtime_profile"] == "squad_versus"
    assert payload["experience_label"] == "Sapiens Consultor"
    assert payload["surface"] == "admin"
    assert payload["checksum"]
    assert payload["cache_key"].startswith("instruction-registry:squad_versus")


def test_instruction_registry_service_resolves_engineering_bundle_without_db():
    payload = InstructionRegistryService.resolve_bundle(runtime_profile="engineering", channel="stable")

    assert payload["runtime_profile"] == "engineering"
    assert payload["experience_label"] == "Sapiens Engenharia"
    assert payload["surface"] == "ops"
    assert "describe_app32_squad_runtime_tool" in payload["startup_sequence"]


def test_instruction_bundle_publishes_safe_discovery_and_retry_rules():
    payload = InstructionRegistryService.resolve_bundle(runtime_profile="squad_cliente", channel="stable")
    rules = " ".join(item["rule"] for item in payload["mandatory_rules"])

    assert payload["bundle_version"] == "2026-07-19.2"
    assert "capability_not_available" in rules
    assert "502, 503 ou 504" in rules
    assert "Nunca repetir mutação automaticamente" in rules
    assert "consultive_get_next_action" in rules
    assert payload["journey_guide"]["version"] == "structuring-journey-v2.1"
    state_keys = [item["key"] for item in payload["journey_guide"]["states"]]
    action_policy = {item["action"]: item["autonomy"] for item in payload["journey_guide"]["action_policy"]}
    assert action_policy["classify_assisted_analysis"] == "must"
    assert "awaiting_engineering_validation" in state_keys
