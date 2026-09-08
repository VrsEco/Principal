from services.sapiens_activation_service import SapiensActivationService
from services.sapiens_engineering_guidance_service import SapiensEngineeringGuidanceService


def test_guidance_manifest_is_read_only_and_manual_model_selection():
    manifest = SapiensEngineeringGuidanceService.build_manifest()

    assert manifest["entry_agent"] == "SE-COORD"
    assert manifest["model_selection"] == "manual_outside_assessment"
    assert manifest["grants_permissions"] is False
    assert manifest["executes_specialists"] is False
    assert manifest["reads_operational_data"] is False
    assert manifest["requires_authenticated_mcp_for_company_evidence"] is True


def test_engineering_activation_exposes_triage_guidance_only_to_engineering():
    activation = SapiensActivationService.resolve_activation(role="admin", squad="engineering")

    assert activation["selected_squad"]["key"] == "engineering"
    assert activation["engineering_guidance"]["interaction_mode"] == "orientation_only"
    assert "escolha do modelo é manual" in activation["activation_guidance"]
    assert "engineering_guidance" not in SapiensActivationService.resolve_activation(
        role="admin", squad="squad_cliente"
    )


def test_non_admin_cannot_use_engineering_guidance_to_bypass_squad_policy():
    try:
        SapiensActivationService.resolve_activation(role="client", squad="engineering")
    except ValueError:
        return
    raise AssertionError("Engineering must remain unavailable to client role")
