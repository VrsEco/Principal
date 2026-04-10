from pathlib import Path

import pytest
from pydantic import ValidationError

from src.core.mcp_operational_readiness_tools import register_operational_readiness_tools
from src.intelligence.mcp_contracts import (
    APP32_OPERATIONAL_READINESS_MANIFEST,
    OperationalReadinessGate,
    OperationalReadinessManifest,
)


DOC = Path(__file__).resolve().parents[1] / "docs" / "governance" / "ai_mcp_operational_readiness.md"


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


def test_operational_readiness_manifest_covers_phases_and_smokes():
    manifest = APP32_OPERATIONAL_READINESS_MANIFEST
    phases = {gate.phase for gate in manifest.gates}

    assert manifest.version == "app32.ai-mcp.operational-readiness.v1"
    assert manifest.tenant_scope_required is True
    assert manifest.sql_freeform_allowed is False
    assert {"contracts", "release", "onboarding", "operations", "go_live"} <= phases
    assert len(manifest.required_smokes) == 5
    assert "AI_MCP_CONTRACT_DRIFT_SUITE_OK 6 True" in manifest.required_smokes


def test_operational_readiness_tool_returns_manifest_phase_and_gate():
    mcp = _FakeMCP()
    register_operational_readiness_tools(mcp)
    tool = mcp.registered["describe_app32_operational_readiness_tool"]

    manifest_payload = tool()
    phase_payload = tool(phase="release")
    gate_payload = tool(gate_id="controlled_go_live")
    missing_payload = tool(phase="missing")

    assert manifest_payload["success"] is True
    assert manifest_payload["data"]["version"] == "app32.ai-mcp.operational-readiness.v1"
    assert phase_payload["success"] is True
    assert len(phase_payload["data"]) == 1
    assert gate_payload["success"] is True
    assert gate_payload["data"]["gate_id"] == "controlled_go_live"
    assert missing_payload["success"] is False
    assert missing_payload["error"]["code"] == "operational_readiness_phase_not_found"


def test_operational_readiness_doc_contains_manifest_tool_and_smoke():
    text = DOC.read_text(encoding="utf-8")

    assert "Readiness Operacional para Abertura Controlada IA/MCP" in text
    assert "APP32_OPERATIONAL_READINESS_MANIFEST" in text
    assert "describe_app32_operational_readiness_tool" in text
    assert "AI_MCP_OPERATIONAL_READINESS_OK 5 5" in text
    assert "AI_MCP_CONTRACT_DRIFT_SUITE_OK 6 True" in text


def test_operational_readiness_contract_rejects_unsafe_manifest():
    gate = OperationalReadinessGate(
        gate_id="contracts_aligned",
        phase="contracts",
        title="Gate válido",
        instruction="Executar validações contratuais completas.",
        required_evidence="Testes verdes.",
        related_artifacts=["tests/test_ai_mcp_contract_drift_suite.py"],
    )

    with pytest.raises(ValidationError):
        OperationalReadinessManifest(
            tenant_scope_required=False,
            readiness_scope=["scope"],
            required_smokes=["AI_MCP_OPERATIONAL_READINESS_OK 5 5"],
            mandatory_discovery_tools=["describe_app32_profile_contracts_tool"],
            gates=[gate],
            opening_criteria=["abrir uso assistido"],
            blocking_conditions=["drift aberto"],
        )
