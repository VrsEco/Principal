from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from .base import MCPSuccessEnvelope, _StrictModel


ReleaseGate = Literal["pre_release", "deploy", "post_deploy", "rollback"]
ReleaseCheckStatus = Literal["required", "recommended", "conditional"]
ReleaseRiskLevel = Literal["low", "medium", "high", "critical"]


class ReleaseChecklistItem(_StrictModel):
    item_id: str = Field(min_length=4, max_length=80)
    title: str = Field(min_length=8, max_length=160)
    gate: ReleaseGate
    status: ReleaseCheckStatus = "required"
    risk: ReleaseRiskLevel = "medium"
    command_hint: str | None = Field(default=None, min_length=4, max_length=500)
    expected_evidence: str = Field(min_length=8, max_length=500)
    blocks_release: bool = True

    @model_validator(mode="after")
    def _validate_blocking_risk(self):
        if self.risk in {"high", "critical"} and not self.blocks_release:
            raise ValueError("Checks high/critical devem bloquear release quando falham.")
        return self


class ReleaseSmokeDefinition(_StrictModel):
    smoke_id: str = Field(min_length=4, max_length=80)
    title: str = Field(min_length=8, max_length=160)
    command: str = Field(min_length=8, max_length=800)
    expected_output: str = Field(min_length=4, max_length=300)
    surfaces: list[str] = Field(default_factory=list, min_length=1)
    tenant_safe: bool = True

    @model_validator(mode="after")
    def _validate_tenant_safe(self):
        if not self.tenant_safe:
            raise ValueError("Smokes IA/MCP devem ser tenant-safe.")
        return self


class ReleaseChecklistManifest(_StrictModel):
    version: str = Field(default="app32.ai-mcp.release-checklist.v1", min_length=1, max_length=80)
    title: str = "Checklist de Release e Smoke Pós-Deploy IA/MCP"
    mandatory_release_branch: str = Field(default="main", min_length=1, max_length=80)
    tenant_scope_required: bool = True
    checklist: list[ReleaseChecklistItem] = Field(default_factory=list, min_length=1)
    smokes: list[ReleaseSmokeDefinition] = Field(default_factory=list, min_length=1)
    rollback_triggers: list[str] = Field(default_factory=list, min_length=1)
    evidence_files: list[str] = Field(default_factory=list, min_length=1)

    @model_validator(mode="after")
    def _validate_manifest(self):
        if not self.tenant_scope_required:
            raise ValueError("Checklist IA/MCP deve exigir tenant_scope_required=True.")
        gates = {item.gate for item in self.checklist}
        for required_gate in ("pre_release", "deploy", "post_deploy", "rollback"):
            if required_gate not in gates:
                raise ValueError(f"Checklist IA/MCP sem gate obrigatório: {required_gate}")
        if not any(smoke.smoke_id == "official_runtime_import" for smoke in self.smokes):
            raise ValueError("Smoke official_runtime_import é obrigatório.")
        return self

    def items_for_gate(self, gate: ReleaseGate | str) -> tuple[ReleaseChecklistItem, ...]:
        normalized = str(gate or "").strip().lower()
        return tuple(item for item in self.checklist if item.gate == normalized)

    def get_smoke(self, smoke_id: str) -> ReleaseSmokeDefinition | None:
        normalized = str(smoke_id or "").strip().lower()
        for smoke in self.smokes:
            if smoke.smoke_id == normalized:
                return smoke
        return None


ReleaseChecklistEnvelope = MCPSuccessEnvelope[ReleaseChecklistManifest | ReleaseChecklistItem | ReleaseSmokeDefinition]


def build_release_checklist_manifest() -> ReleaseChecklistManifest:
    return ReleaseChecklistManifest(
        checklist=[
            ReleaseChecklistItem(
                item_id="tests_contracts",
                title="Executar suíte de contratos IA/MCP",
                gate="pre_release",
                risk="high",
                command_hint="python -m pytest -q tests/test_mcp_* tests/test_core_mcp_* tests/test_official_runtime_smoke.py",
                expected_evidence="Saída pytest com todos os testes IA/MCP relevantes passando.",
            ),
            ReleaseChecklistItem(
                item_id="runtime_topology",
                title="Confirmar runtime oficial e grafos legados protegidos",
                gate="pre_release",
                risk="high",
                command_hint="python -m pytest -q tests/test_intelligence_runtime_classification.py tests/test_intelligence_runtime_guard.py",
                expected_evidence="Runtime oficial aponta para execution/menu_engine/work_agents.graph/tool_catalog e legados seguem allow_for_new_work=False.",
            ),
            ReleaseChecklistItem(
                item_id="mcp_surface_boundaries",
                title="Validar boundaries das surfaces MCP",
                gate="pre_release",
                risk="critical",
                command_hint="python -m pytest -q tests/test_core_mcp_surface_registry.py tests/test_mcp_surface_playbooks.py tests/test_mcp_profile_contracts.py",
                expected_evidence="Surface user sem finance, admin com company_id explícito, analytics sem mutação e ops restrita.",
            ),
            ReleaseChecklistItem(
                item_id="deploy_script",
                title="Executar deploy oficial APP32",
                gate="deploy",
                risk="high",
                command_hint="python C:\\GestaoVersus\\app32\\scripts\\elite_deploy_v3.py",
                expected_evidence="Deploy concluído com código atualizado, dependências OK, migrations OK e uWSGI reiniciado.",
            ),
            ReleaseChecklistItem(
                item_id="post_deploy_imports",
                title="Validar imports IA/MCP em produção",
                gate="post_deploy",
                risk="critical",
                command_hint="Executar smokes official_runtime_import, mcp_surface_manifest e release_checklist_manifest.",
                expected_evidence="Smokes retornam marcadores *_OK esperados via Python no ambiente produtivo.",
            ),
            ReleaseChecklistItem(
                item_id="post_deploy_tool_catalog",
                title="Validar catálogo MCP/Sapiens após deploy",
                gate="post_deploy",
                risk="high",
                command_hint="python -c \"import app; from src.intelligence.tool_catalog import catalog; print(bool(catalog.get_langchain_tools()))\"",
                expected_evidence="Catálogo importável e com tools/capabilities disponíveis.",
            ),
            ReleaseChecklistItem(
                item_id="rollback_prepare",
                title="Preparar rollback caso smoke falhe",
                gate="rollback",
                risk="critical",
                command_hint="Reverter commit ou desabilitar capability/registrador afetado, redeploy e repetir smokes.",
                expected_evidence="Commit anterior ou capability congelada com smoke pós-rollback verde.",
            ),
        ],
        smokes=[
            ReleaseSmokeDefinition(
                smoke_id="official_runtime_import",
                title="Import e compilação do runtime oficial",
                command="python -c \"import app; from src.intelligence.work_agents.graph import create_work_agent_workflow; print('AI_MCP_RELEASE_RUNTIME_OK', hasattr(create_work_agent_workflow(),'invoke'))\"",
                expected_output="AI_MCP_RELEASE_RUNTIME_OK True",
                surfaces=["sapiens", "mcp"],
            ),
            ReleaseSmokeDefinition(
                smoke_id="mcp_surface_manifest",
                title="Manifestos user/admin/analytics/ops disponíveis",
                command="python -c \"import app; from src.core.mcp_surface_registry import get_surface_manifest; print('AI_MCP_RELEASE_SURFACES_OK', all(bool(get_surface_manifest(s)) for s in ['user','admin','analytics','ops']))\"",
                expected_output="AI_MCP_RELEASE_SURFACES_OK True",
                surfaces=["user", "admin", "analytics", "ops"],
            ),
            ReleaseSmokeDefinition(
                smoke_id="release_checklist_manifest",
                title="Manifesto de release IA/MCP disponível",
                command="python -c \"import app; from src.intelligence.mcp_contracts import APP32_RELEASE_CHECKLIST_MANIFEST; print('AI_MCP_RELEASE_CHECKLIST_OK', len(APP32_RELEASE_CHECKLIST_MANIFEST.checklist), len(APP32_RELEASE_CHECKLIST_MANIFEST.smokes))\"",
                expected_output="AI_MCP_RELEASE_CHECKLIST_OK 7 3",
                surfaces=["mcp"],
            ),
        ],
        rollback_triggers=[
            "Falha de import do app ou de qualquer contrato IA/MCP após deploy.",
            "Smoke de runtime oficial sem CompiledGraph invocável.",
            "Surface user expondo finance ou admin/analytics/ops indevidamente.",
            "Evento crítico de tenant/security relacionado à release.",
            "Erro 500 recorrente em endpoints ou tools MCP afetadas pela mudança.",
        ],
        evidence_files=[
            "scripts/aa_j_31_group*_completed_result.json",
            "logs de deploy do elite_deploy_v3.py",
            "saída dos smokes pós-deploy com marcador *_OK",
        ],
    )


APP32_RELEASE_CHECKLIST_MANIFEST = build_release_checklist_manifest()


__all__ = [
    "APP32_RELEASE_CHECKLIST_MANIFEST",
    "ReleaseCheckStatus",
    "ReleaseChecklistEnvelope",
    "ReleaseChecklistItem",
    "ReleaseChecklistManifest",
    "ReleaseGate",
    "ReleaseRiskLevel",
    "ReleaseSmokeDefinition",
    "build_release_checklist_manifest",
]
