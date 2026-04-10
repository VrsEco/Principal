from pathlib import Path

import pytest
from pydantic import ValidationError

from src.core.mcp_tool_freeze_tools import register_tool_freeze_tools
from src.intelligence.mcp_contracts import (
    APP32_TOOL_FREEZE_MANIFEST,
    ToolFreezeManifest,
    ToolFreezeProcedureStep,
    ToolFreezeTriggerRule,
)


DOC = Path(__file__).resolve().parents[1] / "docs" / "governance" / "ai_mcp_tool_freeze_procedure.md"


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


def test_tool_freeze_manifest_covers_critical_triggers_and_steps():
    manifest = APP32_TOOL_FREEZE_MANIFEST
    triggers = {rule.trigger for rule in manifest.triggers}

    assert manifest.version == "app32.ai-mcp.tool-freeze.v1"
    assert manifest.tenant_scope_required is True
    assert {"cross_tenant_risk", "rbac_bypass", "unsafe_mutation"} <= triggers
    assert len(manifest.freeze_steps) == 4
    assert len(manifest.unfreeze_steps) == 3
    assert "AI_MCP_RELEASE_RUNTIME_OK True" in manifest.required_smokes
    assert all(rule.blocks_runtime for rule in manifest.triggers if rule.severity == "critical")


def test_tool_freeze_mcp_tool_describes_manifest_and_trigger():
    mcp = _FakeMCP()
    register_tool_freeze_tools(mcp)
    tool = mcp.registered["describe_app32_tool_freeze_procedure_tool"]

    manifest_payload = tool()
    assert manifest_payload["success"] is True
    assert manifest_payload["data"]["version"] == "app32.ai-mcp.tool-freeze.v1"

    trigger_payload = tool("cross_tenant_risk")
    assert trigger_payload["success"] is True
    assert trigger_payload["data"]["severity"] == "critical"
    assert trigger_payload["data"]["recommended_action"] == "disable_capability"

    missing_payload = tool("missing")
    assert missing_payload["success"] is False
    assert missing_payload["error"]["code"] == "tool_freeze_trigger_not_found"


def test_tool_freeze_doc_contains_smoke_and_mcp_usage():
    text = DOC.read_text(encoding="utf-8")

    assert "Procedimento de Congelamento de Tool Insegura IA/MCP" in text
    assert "APP32_TOOL_FREEZE_MANIFEST" in text
    assert "describe_app32_tool_freeze_procedure_tool" in text
    assert "AI_MCP_TOOL_FREEZE_OK 7 4" in text
    assert "cross_tenant_risk" in text
    assert "rbac_bypass" in text


def test_tool_freeze_contract_rejects_unsafe_critical_trigger_and_missing_required_trigger():
    with pytest.raises(ValidationError):
        ToolFreezeTriggerRule(
            trigger="cross_tenant_risk",
            severity="critical",
            description="Trigger crítico deve bloquear runtime.",
            recommended_action="disable_capability",
            blocks_runtime=False,
        )

    step = ToolFreezeProcedureStep(
        step_id="step",
        title="Passo válido",
        owner="arquiteto",
        action="Executar uma ação segura e auditável.",
        expected_evidence="Evidência de execução.",
    )
    trigger = ToolFreezeTriggerRule(
        trigger="runtime_error",
        severity="high",
        description="Erro de runtime recorrente.",
        recommended_action="rollback_release",
    )

    with pytest.raises(ValidationError):
        ToolFreezeManifest(
            triggers=[trigger],
            freeze_steps=[step],
            unfreeze_steps=[step],
            required_smokes=["AI_MCP_RELEASE_RUNTIME_OK True"],
            evidence_files=["evidência"],
        )
