from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from .base import MCPSuccessEnvelope, _StrictModel


ReadinessPhase = Literal["contracts", "release", "onboarding", "operations", "go_live"]
ReadinessStatus = Literal["required", "conditional", "informational"]


class OperationalReadinessGate(_StrictModel):
    gate_id: str = Field(min_length=4, max_length=80)
    phase: ReadinessPhase
    title: str = Field(min_length=8, max_length=160)
    status: ReadinessStatus = "required"
    instruction: str = Field(min_length=16, max_length=600)
    required_evidence: str = Field(min_length=8, max_length=400)
    related_artifacts: list[str] = Field(default_factory=list, min_length=1)


class OperationalReadinessManifest(_StrictModel):
    version: str = Field(default="app32.ai-mcp.operational-readiness.v1", min_length=1, max_length=80)
    title: str = "Readiness Operacional para Abertura Controlada IA/MCP"
    tenant_scope_required: bool = True
    sql_freeform_allowed: bool = False
    readiness_scope: list[str] = Field(default_factory=list, min_length=1)
    required_smokes: list[str] = Field(default_factory=list, min_length=1)
    mandatory_discovery_tools: list[str] = Field(default_factory=list, min_length=1)
    gates: list[OperationalReadinessGate] = Field(default_factory=list, min_length=1)
    opening_criteria: list[str] = Field(default_factory=list, min_length=1)
    blocking_conditions: list[str] = Field(default_factory=list, min_length=1)

    @model_validator(mode="after")
    def _validate_manifest(self):
        if not self.tenant_scope_required:
            raise ValueError("Readiness operacional exige tenant_scope_required=True.")
        if self.sql_freeform_allowed:
            raise ValueError("Readiness operacional não pode liberar SQL livre.")
        phases = {gate.phase for gate in self.gates}
        if not {"contracts", "release", "onboarding", "operations", "go_live"}.issubset(phases):
            raise ValueError("Manifesto de readiness deve cobrir todas as fases operacionais.")
        return self

    def get_gate(self, gate_id: str) -> OperationalReadinessGate | None:
        normalized = str(gate_id or "").strip().lower()
        for gate in self.gates:
            if gate.gate_id == normalized:
                return gate
        return None

    def get_phase(self, phase: str) -> list[OperationalReadinessGate]:
        normalized = str(phase or "").strip().lower()
        return [gate for gate in self.gates if gate.phase == normalized]


OperationalReadinessEnvelope = MCPSuccessEnvelope[
    OperationalReadinessManifest | OperationalReadinessGate | list[OperationalReadinessGate]
]


def build_operational_readiness_manifest() -> OperationalReadinessManifest:
    return OperationalReadinessManifest(
        readiness_scope=[
            "surfaces user/admin/analytics/ops prontas para uso controlado",
            "agentes externos onboarding-safe",
            "runtime oficial e contratos MCP coerentes",
            "monitoramento, freeze e rollback operacionalizados",
        ],
        required_smokes=[
            "MCP_USER_ADMIN_RUNBOOK_SMOKE_OK True True",
            "AI_MCP_RELEASE_CHECKLIST_OK 7 3",
            "AI_MCP_TOOL_FREEZE_OK 7 4",
            "AI_MCP_EXTERNAL_ONBOARDING_OK 4 5",
            "AI_MCP_CONTRACT_DRIFT_SUITE_OK 6 True",
        ],
        mandatory_discovery_tools=[
            "describe_app32_profile_contracts_tool",
            "describe_app32_surface_playbooks_tool",
            "describe_app32_domain_playbooks_tool",
            "describe_app32_permission_matrix_tool",
            "describe_app32_release_checklist_tool",
            "describe_app32_tool_freeze_procedure_tool",
            "describe_app32_external_ai_onboarding_tool",
            "describe_app32_usage_dashboard_tool",
        ],
        gates=[
            OperationalReadinessGate(
                gate_id="contracts_aligned",
                phase="contracts",
                title="Contratos MCP alinhados e sem drift aberto",
                instruction="Validar profiles, playbooks, permission_matrix, capabilities e tool_policy com a suíte canônica de drift.",
                required_evidence="Suítes de contrato/drift verdes e smoke AI_MCP_CONTRACT_DRIFT_SUITE_OK.",
                related_artifacts=[
                    "tests/test_ai_mcp_contract_drift_suite.py",
                    "src.intelligence.mcp_contracts.permission_matrix",
                ],
            ),
            OperationalReadinessGate(
                gate_id="release_smoke_green",
                phase="release",
                title="Release e smoke pós-deploy verdes",
                instruction="Executar checklist oficial de release, deploy e smokes pós-deploy antes de abrir uso controlado.",
                required_evidence="Marcadores MCP_USER_ADMIN_RUNBOOK_SMOKE_OK e AI_MCP_RELEASE_CHECKLIST_OK presentes.",
                related_artifacts=[
                    "docs/governance/ai_mcp_release_smoke_checklist.md",
                    "docs/governance/mcp_user_admin_production_runbook.md",
                ],
            ),
            OperationalReadinessGate(
                gate_id="external_ai_onboarding_ready",
                phase="onboarding",
                title="Onboarding de IAs externas operacionalizado",
                instruction="Garantir intake, desenho de acesso, registro, validação e operação monitorada para qualquer agente externo.",
                required_evidence="Manual de onboarding ativo e smoke AI_MCP_EXTERNAL_ONBOARDING_OK.",
                related_artifacts=[
                    "docs/governance/external_ai_mcp_onboarding_manual.md",
                    "src.intelligence.mcp_contracts.external_ai_onboarding",
                ],
            ),
            OperationalReadinessGate(
                gate_id="monitoring_and_freeze_ready",
                phase="operations",
                title="Monitoramento, dashboard e freeze disponíveis",
                instruction="Confirmar dashboard/relatório de uso, gatilhos de congelamento e rollback conhecidos para resposta rápida.",
                required_evidence="Especificação de dashboard e procedimento de tool freeze disponíveis para operação.",
                related_artifacts=[
                    "docs/governance/ai_mcp_usage_dashboard_spec.md",
                    "docs/governance/ai_mcp_tool_freeze_procedure.md",
                ],
            ),
            OperationalReadinessGate(
                gate_id="controlled_go_live",
                phase="go_live",
                title="Abertura controlada com menor privilégio",
                instruction="Abrir primeiro para uso assistido/piloto, com surfaces e perfis estritamente aderentes ao contrato e sem liberação irrestrita.",
                required_evidence="Critérios de abertura, bloqueio e rollback documentados e aprovados pelo time técnico.",
                related_artifacts=[
                    "docs/governance/ai_mcp_operational_readiness.md",
                    "docs/governance/ai_mcp_permission_matrix.md",
                ],
            ),
        ],
        opening_criteria=[
            "usar apenas runtime oficial e surfaces MCP canonizadas",
            "operar com menor privilégio por perfil e surface",
            "abrir primeiro para homologação interna, piloto e uso assistido",
            "exigir company_id explícito nas surfaces e domínios sensíveis",
            "manter monitoramento, freeze e rollback disponíveis",
        ],
        blocking_conditions=[
            "drift aberto entre contrato, catálogo e policy",
            "smoke pós-deploy falhando",
            "risco cross-tenant ou bypass RBAC",
            "tool sensível sem freeze/rollback operacionalizado",
            "abertura irrestrita sem onboarding e readiness documentados",
        ],
    )


APP32_OPERATIONAL_READINESS_MANIFEST = build_operational_readiness_manifest()


__all__ = [
    "APP32_OPERATIONAL_READINESS_MANIFEST",
    "OperationalReadinessEnvelope",
    "OperationalReadinessGate",
    "OperationalReadinessManifest",
    "ReadinessPhase",
    "ReadinessStatus",
    "build_operational_readiness_manifest",
]
