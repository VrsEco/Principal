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
    assert manifest["conversation_routing"] == {
        "state_owner": "client_runtime",
        "scope": "current_conversation_only",
        "activate_with": "Squad Engenharia On",
        "deactivate_with": "Squad Engenharia Off",
        "route_each_subsequent_request": True,
        "request_payload": "engineering_task",
        "expires_on": ("deactivation", "new_conversation", "identity_change"),
    }


def test_engineering_activation_exposes_triage_guidance_only_in_local_mode():
    activation = SapiensActivationService.resolve_activation(
        role="admin", squad="engineering", include_local_only=True
    )

    assert activation["selected_squad"]["key"] == "engineering"
    assert activation["engineering_guidance"]["interaction_mode"] == "orientation_only"
    assert "escolha do modelo é manual" in activation["activation_guidance"]
    assert "mantenha o roteamento SE-COORD" in activation["activation_guidance"]
    assert activation["startup_tools"] == []
    assert "engineering_guidance" not in SapiensActivationService.resolve_activation(
        role="admin", squad="squad_cliente"
    )


def test_remote_default_and_non_admin_cannot_use_engineering_guidance():
    try:
        SapiensActivationService.resolve_activation(role="admin", squad="engineering")
    except ValueError:
        pass
    else:
        raise AssertionError("Engineering must remain unavailable by remote default")
    with __import__("pytest").raises(ValueError):
        SapiensActivationService.resolve_activation(
            role="client", squad="engineering", include_local_only=True
        )
