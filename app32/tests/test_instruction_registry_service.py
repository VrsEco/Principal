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

    assert payload["bundle_version"] == "2026-08-28.5"
    assert "capability_not_available" in rules
    assert "502, 503 ou 504" in rules
    assert "Nunca repetir mutação automaticamente" in rules
    assert "consultive_get_next_action" in rules
    assert "POP como seletivo e compartilhável" in rules
    assert "progressivamente do gatilho ao objetivo" in rules
    assert "process-modeling-official-v1.0" in rules
    assert "no máximo três perguntas" in rules
    assert "Pesquisar referências externas" in rules
    assert "POP azul" in rules
    assert "completion policy" in rules
    assert payload["journey_guide"]["version"] == "structuring-journey-v2.1"
    state_keys = [item["key"] for item in payload["journey_guide"]["states"]]
    action_policy = {item["action"]: item["autonomy"] for item in payload["journey_guide"]["action_policy"]}
    assert action_policy["classify_assisted_analysis"] == "must"
    assert "awaiting_engineering_validation" in state_keys


def test_instruction_bundle_specializes_process_modeling_by_squad() -> None:
    client = InstructionRegistryService.resolve_bundle(
        runtime_profile="squad_cliente",
        harness_key="harness_operacional_cliente_v1",
    )
    versus = InstructionRegistryService.resolve_bundle(
        runtime_profile="squad_versus",
        harness_key="harness_business_architect_versus_v1",
    )

    assert client["agent_key"] == "SC-OPS"
    assert versus["agent_key"] == "SV-BUSINESS-ARCHITECT"
    assert any("não publicar bpmn" in item.lower() for item in client["forbidden_actions"])
    assert any("SIPOC nos dois sentidos" in item["rule"] for item in client["handoff_rules"])
    assert any("collecting_evidence" in item["rule"] for item in client["handoff_rules"])
    assert any("evidência operacional faltante" in item["rule"] for item in client["handoff_rules"])
    assert any("não validar apenas pela cor" in item["rule"] for item in client["handoff_rules"])
    assert any("publicar somente" in item["rule"] for item in versus["handoff_rules"])
    assert any("objetivo ao gatilho pelo SIPOC" in item["rule"] for item in versus["handoff_rules"])
    assert any("completing_operational_model" in item["rule"] for item in versus["handoff_rules"])
    assert any("Identidade Organizacional" in item["rule"] for item in versus["handoff_rules"])
    assert any("linguagem visual apenas como apoio" in item["rule"] for item in versus["handoff_rules"])
