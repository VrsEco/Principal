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
