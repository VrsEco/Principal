from pathlib import Path

import pytest
from pydantic import ValidationError

from src.core.mcp_release_checklist_tools import register_release_checklist_tools
from src.intelligence.mcp_contracts import (
    APP32_RELEASE_CHECKLIST_MANIFEST,
    ReleaseChecklistItem,
    ReleaseChecklistManifest,
    ReleaseSmokeDefinition,
)


DOC = Path(__file__).resolve().parents[1] / "docs" / "governance" / "ai_mcp_release_smoke_checklist.md"


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


def test_release_checklist_manifest_covers_required_gates_and_smokes():
    manifest = APP32_RELEASE_CHECKLIST_MANIFEST
    gates = {item.gate for item in manifest.checklist}
    smoke_ids = {smoke.smoke_id for smoke in manifest.smokes}

    assert manifest.version == "app32.ai-mcp.release-checklist.v1"
    assert manifest.tenant_scope_required is True
    assert {"pre_release", "deploy", "post_deploy", "rollback"} <= gates
    assert {
        "official_runtime_import",
        "mcp_surface_manifest",
        "release_checklist_manifest",
    } <= smoke_ids
    assert all(item.blocks_release for item in manifest.checklist if item.risk in {"high", "critical"})
    assert all(smoke.tenant_safe for smoke in manifest.smokes)


def test_release_checklist_tool_describes_manifest_gate_and_smoke():
    mcp = _FakeMCP()
    register_release_checklist_tools(mcp)
    tool = mcp.registered["describe_app32_release_checklist_tool"]

    manifest_payload = tool()
    assert manifest_payload["success"] is True
    assert manifest_payload["data"]["version"] == "app32.ai-mcp.release-checklist.v1"

    gate_payload = tool(gate="post_deploy")
    assert gate_payload["success"] is True
    assert all(item["gate"] == "post_deploy" for item in gate_payload["data"])

    smoke_payload = tool(smoke_id="release_checklist_manifest")
    assert smoke_payload["success"] is True
    assert smoke_payload["data"]["expected_output"] == "AI_MCP_RELEASE_CHECKLIST_OK 7 3"

    missing_payload = tool(gate="unknown")
    assert missing_payload["success"] is False
    assert missing_payload["error"]["code"] == "release_checklist_item_not_found"


def test_release_checklist_doc_contains_smoke_markers_and_rollback():
    text = DOC.read_text(encoding="utf-8")

    assert "Checklist de Release e Smoke Pós-Deploy IA/MCP" in text
    assert "APP32_RELEASE_CHECKLIST_MANIFEST" in text
    assert "describe_app32_release_checklist_tool" in text
    assert "AI_MCP_RELEASE_RUNTIME_OK True" in text
    assert "AI_MCP_RELEASE_SURFACES_OK True" in text
    assert "AI_MCP_RELEASE_CHECKLIST_OK 7 3" in text
    assert "## 3.4 Rollback" in text


def test_release_checklist_contract_rejects_unsafe_items_and_smokes():
    with pytest.raises(ValidationError):
        ReleaseChecklistItem(
            item_id="unsafe",
            title="Check crítico inseguro",
            gate="pre_release",
            risk="critical",
            expected_evidence="Deveria bloquear release.",
            blocks_release=False,
        )

    with pytest.raises(ValidationError):
        ReleaseSmokeDefinition(
            smoke_id="unsafe_smoke",
            title="Smoke sem tenant safety",
            command="python -c pass",
            expected_output="OKOK",
            surfaces=["mcp"],
            tenant_safe=False,
        )


def test_release_checklist_manifest_rejects_missing_required_gate():
    item = ReleaseChecklistItem(
        item_id="pre_only",
        title="Somente pré release",
        gate="pre_release",
        expected_evidence="Teste apenas para validação.",
    )
    smoke = ReleaseSmokeDefinition(
        smoke_id="official_runtime_import",
        title="Runtime oficial",
        command="python -c pass",
        expected_output="OKOK",
        surfaces=["mcp"],
    )

    with pytest.raises(ValidationError):
        ReleaseChecklistManifest(
            checklist=[item],
            smokes=[smoke],
            rollback_triggers=["falha"],
            evidence_files=["evidência"],
        )

