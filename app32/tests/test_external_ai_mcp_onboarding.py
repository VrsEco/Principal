from pathlib import Path

import pytest
from pydantic import ValidationError

from src.core.mcp_external_ai_onboarding_tools import register_external_ai_onboarding_tools
from src.intelligence.mcp_contracts import (
    APP32_EXTERNAL_AI_ONBOARDING_MANIFEST,
    ExternalAIOnboardingManifest,
    ExternalAIOnboardingStep,
    ExternalAISurfaceAccessRule,
)


DOC = Path(__file__).resolve().parents[1] / "docs" / "governance" / "external_ai_mcp_onboarding_manual.md"


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


def test_external_ai_onboarding_manifest_covers_surfaces_and_phases():
    manifest = APP32_EXTERNAL_AI_ONBOARDING_MANIFEST
    surfaces = {rule.surface for rule in manifest.surface_access_rules}
    phases = {step.phase for step in manifest.steps}

    assert manifest.version == "app32.ai-mcp.external-ai-onboarding.v1"
    assert manifest.tenant_scope_required is True
    assert manifest.sql_freeform_allowed is False
    assert {"user", "admin", "analytics", "ops"} <= surfaces
    assert {"intake", "access_design", "registration", "validation", "operation"} <= phases
    assert "AI_MCP_EXTERNAL_ONBOARDING_OK 4 5" in manifest.go_live_smokes


def test_external_ai_onboarding_surface_boundaries():
    manifest = APP32_EXTERNAL_AI_ONBOARDING_MANIFEST
    user = manifest.get_surface_rule("user")
    admin = manifest.get_surface_rule("admin")
    ops = manifest.get_surface_rule("ops")

    assert user is not None
    assert "chatgpt" in user.allowed_provider_types
    assert "admin_tecnico" not in user.allowed_profiles
    assert admin is not None
    assert admin.human_approval_required is True
    assert "chatgpt" not in admin.allowed_provider_types
    assert ops is not None
    assert ops.allowed_provider_types == ["internal_agent"]
    assert ops.allowed_profiles == ["admin_tecnico"]


def test_external_ai_onboarding_mcp_tool_describes_manifest_and_surface():
    mcp = _FakeMCP()
    register_external_ai_onboarding_tools(mcp)
    tool = mcp.registered["describe_app32_external_ai_onboarding_tool"]

    manifest_payload = tool()
    assert manifest_payload["success"] is True
    assert manifest_payload["data"]["version"] == "app32.ai-mcp.external-ai-onboarding.v1"

    surface_payload = tool("analytics")
    assert surface_payload["success"] is True
    assert surface_payload["data"]["surface"] == "analytics"

    missing_payload = tool("missing")
    assert missing_payload["success"] is False
    assert missing_payload["error"]["code"] == "external_ai_onboarding_surface_not_found"


def test_external_ai_onboarding_doc_contains_smoke_and_forbidden_patterns():
    text = DOC.read_text(encoding="utf-8")

    assert "Manual de Onboarding de IAs Externas via MCP" in text
    assert "APP32_EXTERNAL_AI_ONBOARDING_MANIFEST" in text
    assert "describe_app32_external_ai_onboarding_tool" in text
    assert "AI_MCP_EXTERNAL_ONBOARDING_OK 4 5" in text
    assert "Não liberar SQL livre" in text
    assert "Não compartilhar tokens" in text


def test_external_ai_onboarding_contract_rejects_unsafe_surface_and_incomplete_manifest():
    with pytest.raises(ValidationError):
        ExternalAISurfaceAccessRule(
            surface="admin",
            allowed_provider_types=["custom_agent"],
            allowed_profiles=["administrador"],
            required_discovery_tools=["list_admin_app32_capabilities"],
            human_approval_required=False,
        )

    step = ExternalAIOnboardingStep(
        step_id="only",
        phase="intake",
        title="Passo único",
        instruction="Registrar provider e escopo inicial.",
        required_evidence="Ficha preenchida.",
    )
    rule = ExternalAISurfaceAccessRule(
        surface="user",
        allowed_provider_types=["chatgpt"],
        allowed_profiles=["colaborador"],
        required_discovery_tools=["list_user_app32_capabilities"],
    )
    with pytest.raises(ValidationError):
        ExternalAIOnboardingManifest(
            supported_provider_types=["chatgpt"],
            required_global_discovery_tools=["list_app32_capabilities"],
            surface_access_rules=[rule],
            steps=[step],
            go_live_smokes=["AI_MCP_EXTERNAL_ONBOARDING_OK 4 5"],
            forbidden_patterns=["sem sql livre"],
        )
