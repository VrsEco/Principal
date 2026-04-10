from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from .base import MCPSuccessEnvelope, _StrictModel


ToolFreezeTrigger = Literal[
    "cross_tenant_risk",
    "rbac_bypass",
    "unsafe_mutation",
    "financial_exposure",
    "secret_exposure",
    "runtime_error",
    "catalog_contract_drift",
]
ToolFreezeAction = Literal["disable_capability", "remove_surface_scope", "force_human_gate", "rollback_release"]
ToolFreezeSeverity = Literal["high", "critical"]


class ToolFreezeProcedureStep(_StrictModel):
    step_id: str = Field(min_length=4, max_length=80)
    title: str = Field(min_length=8, max_length=160)
    owner: Literal["release_engineer", "backend_api", "ai_engineer", "qa_automation", "arquiteto"]
    action: str = Field(min_length=12, max_length=500)
    expected_evidence: str = Field(min_length=8, max_length=500)
    blocks_unfreeze: bool = True


class ToolFreezeTriggerRule(_StrictModel):
    trigger: ToolFreezeTrigger
    severity: ToolFreezeSeverity
    description: str = Field(min_length=16, max_length=320)
    recommended_action: ToolFreezeAction
    blocks_runtime: bool = True

    @model_validator(mode="after")
    def _validate_critical_blocks_runtime(self):
        if self.severity == "critical" and not self.blocks_runtime:
            raise ValueError("Trigger crítico deve bloquear runtime/tool.")
        return self


class ToolFreezeManifest(_StrictModel):
    version: str = Field(default="app32.ai-mcp.tool-freeze.v1", min_length=1, max_length=80)
    title: str = "Procedimento de Congelamento de Tool Insegura IA/MCP"
    tenant_scope_required: bool = True
    triggers: list[ToolFreezeTriggerRule] = Field(default_factory=list, min_length=1)
    freeze_steps: list[ToolFreezeProcedureStep] = Field(default_factory=list, min_length=1)
    unfreeze_steps: list[ToolFreezeProcedureStep] = Field(default_factory=list, min_length=1)
    required_smokes: list[str] = Field(default_factory=list, min_length=1)
    evidence_files: list[str] = Field(default_factory=list, min_length=1)

    @model_validator(mode="after")
    def _validate_manifest(self):
        if not self.tenant_scope_required:
            raise ValueError("Congelamento de tool IA/MCP exige tenant_scope_required=True.")
        trigger_set = {rule.trigger for rule in self.triggers}
        for required in ("cross_tenant_risk", "rbac_bypass", "unsafe_mutation"):
            if required not in trigger_set:
                raise ValueError(f"Trigger obrigatório ausente: {required}")
        if not any("AI_MCP_RELEASE" in smoke for smoke in self.required_smokes):
            raise ValueError("Smokes de release IA/MCP são obrigatórios para congelamento.")
        return self

    def get_trigger(self, trigger: str) -> ToolFreezeTriggerRule | None:
        normalized = str(trigger or "").strip().lower()
        for rule in self.triggers:
            if rule.trigger == normalized:
                return rule
        return None


ToolFreezeEnvelope = MCPSuccessEnvelope[ToolFreezeManifest | ToolFreezeTriggerRule]


def build_tool_freeze_manifest() -> ToolFreezeManifest:
    return ToolFreezeManifest(
        triggers=[
            ToolFreezeTriggerRule(
                trigger="cross_tenant_risk",
                severity="critical",
                description="Qualquer evidência ou suspeita de vazamento entre empresas/tenants.",
                recommended_action="disable_capability",
            ),
            ToolFreezeTriggerRule(
                trigger="rbac_bypass",
                severity="critical",
                description="Tool acessível por perfil/surface sem permissão contratual.",
                recommended_action="remove_surface_scope",
            ),
            ToolFreezeTriggerRule(
                trigger="unsafe_mutation",
                severity="critical",
                description="Mutação sem confirmação humana, company_id ou contrato CRUD seguro.",
                recommended_action="force_human_gate",
            ),
            ToolFreezeTriggerRule(
                trigger="financial_exposure",
                severity="critical",
                description="Exposição financeira indevida, mutação financeira pela user surface ou dado bancário sensível.",
                recommended_action="disable_capability",
            ),
            ToolFreezeTriggerRule(
                trigger="secret_exposure",
                severity="critical",
                description="Exposição de token, senha, cookie, autorização ou segredo em payload/metadata.",
                recommended_action="rollback_release",
            ),
            ToolFreezeTriggerRule(
                trigger="runtime_error",
                severity="high",
                description="Erro 500 recorrente ou falha de runtime causada por tool MCP/Sapiens recém-alterada.",
                recommended_action="rollback_release",
            ),
            ToolFreezeTriggerRule(
                trigger="catalog_contract_drift",
                severity="high",
                description="Divergência entre tool registrada, capability, contrato CRUD, playbook e política RBAC.",
                recommended_action="remove_surface_scope",
            ),
        ],
        freeze_steps=[
            ToolFreezeProcedureStep(
                step_id="identify_scope",
                title="Identificar tool, surface, domínio e tenant afetado",
                owner="arquiteto",
                action="Coletar tool_name, capability, domain, surface, company_id, user_id, trace_id e evidência do incidente.",
                expected_evidence="Registro com escopo de impacto e trigger de congelamento classificado.",
            ),
            ToolFreezeProcedureStep(
                step_id="disable_or_scope_down",
                title="Desabilitar capability ou remover surface scope",
                owner="backend_api",
                action="Remover temporariamente a capability da surface afetada, forçar human_gate ou aplicar rollback do registrador.",
                expected_evidence="Diff do catálogo/política demonstrando bloqueio da exposição insegura.",
            ),
            ToolFreezeProcedureStep(
                step_id="deploy_freeze",
                title="Publicar congelamento",
                owner="release_engineer",
                action="Executar deploy oficial e smokes IA/MCP obrigatórios.",
                expected_evidence="Deploy verde e marcador AI_MCP_RELEASE_*_OK esperado.",
            ),
            ToolFreezeProcedureStep(
                step_id="qa_regression",
                title="Executar regressão de surfaces e política",
                owner="qa_automation",
                action="Executar testes de surface registry, profile contracts, release checklist e policy relacionada.",
                expected_evidence="Pytest verde para a suíte IA/MCP impactada.",
            ),
        ],
        unfreeze_steps=[
            ToolFreezeProcedureStep(
                step_id="root_cause",
                title="Corrigir causa raiz antes de reabilitar",
                owner="ai_engineer",
                action="Corrigir contrato, prompt, policy, service ou tool que causou o congelamento.",
                expected_evidence="Patch com teste reproduzindo e corrigindo a falha.",
            ),
            ToolFreezeProcedureStep(
                step_id="security_review",
                title="Revisar multi-tenancy e RBAC",
                owner="arquiteto",
                action="Validar company_id, profile, surface, domain, risk e human_gate antes de reabilitar.",
                expected_evidence="Checklist de segurança aprovado e sem risco cross-tenant.",
            ),
            ToolFreezeProcedureStep(
                step_id="unfreeze_deploy",
                title="Reabilitar com deploy e smoke",
                owner="release_engineer",
                action="Reabilitar capability/scope, executar deploy oficial e smokes pós-deploy.",
                expected_evidence="Smokes pós-deploy verdes e evidência de reabilitação segura.",
            ),
        ],
        required_smokes=[
            "AI_MCP_RELEASE_RUNTIME_OK True",
            "AI_MCP_RELEASE_SURFACES_OK True",
            "AI_MCP_RELEASE_CHECKLIST_OK 7 3",
        ],
        evidence_files=[
            "scripts/aa_j_31_group07_tool_freeze_completed_result.json",
            "logs de deploy do elite_deploy_v3.py",
            "saída de pytest da suíte IA/MCP impactada",
        ],
    )


APP32_TOOL_FREEZE_MANIFEST = build_tool_freeze_manifest()


__all__ = [
    "APP32_TOOL_FREEZE_MANIFEST",
    "ToolFreezeAction",
    "ToolFreezeEnvelope",
    "ToolFreezeManifest",
    "ToolFreezeProcedureStep",
    "ToolFreezeSeverity",
    "ToolFreezeTrigger",
    "ToolFreezeTriggerRule",
    "build_tool_freeze_manifest",
]
