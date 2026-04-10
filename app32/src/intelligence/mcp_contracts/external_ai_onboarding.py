from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from .base import MCPSuccessEnvelope, _StrictModel


ExternalAIProviderType = Literal["chatgpt", "claude", "gemini", "custom_agent", "internal_agent"]
ExternalAIOnboardingPhase = Literal["intake", "access_design", "registration", "validation", "operation"]


class ExternalAIOnboardingStep(_StrictModel):
    step_id: str = Field(min_length=4, max_length=80)
    phase: ExternalAIOnboardingPhase
    title: str = Field(min_length=8, max_length=160)
    instruction: str = Field(min_length=16, max_length=600)
    required_evidence: str = Field(min_length=8, max_length=500)
    blocks_go_live: bool = True


class ExternalAISurfaceAccessRule(_StrictModel):
    surface: Literal["user", "admin", "analytics", "ops"]
    allowed_provider_types: list[ExternalAIProviderType] = Field(default_factory=list, min_length=1)
    allowed_profiles: list[str] = Field(default_factory=list, min_length=1)
    required_discovery_tools: list[str] = Field(default_factory=list, min_length=1)
    tenant_scope_required: bool = True
    human_approval_required: bool = True

    @model_validator(mode="after")
    def _validate_surface_access(self):
        if not self.tenant_scope_required:
            raise ValueError("Onboarding de IA externa exige tenant_scope_required=True.")
        if self.surface in {"admin", "ops"} and not self.human_approval_required:
            raise ValueError("Surfaces privilegiadas exigem aprovação humana.")
        if self.surface == "user" and "admin_tecnico" in self.allowed_profiles:
            raise ValueError("Surface user não deve ser onboarding padrão de admin_tecnico.")
        return self


class ExternalAIOnboardingManifest(_StrictModel):
    version: str = Field(default="app32.ai-mcp.external-ai-onboarding.v1", min_length=1, max_length=80)
    title: str = "Manual de Onboarding de IAs Externas via MCP"
    tenant_scope_required: bool = True
    sql_freeform_allowed: bool = False
    supported_provider_types: list[ExternalAIProviderType] = Field(default_factory=list, min_length=1)
    required_global_discovery_tools: list[str] = Field(default_factory=list, min_length=1)
    surface_access_rules: list[ExternalAISurfaceAccessRule] = Field(default_factory=list, min_length=1)
    steps: list[ExternalAIOnboardingStep] = Field(default_factory=list, min_length=1)
    go_live_smokes: list[str] = Field(default_factory=list, min_length=1)
    forbidden_patterns: list[str] = Field(default_factory=list, min_length=1)

    @model_validator(mode="after")
    def _validate_manifest(self):
        if not self.tenant_scope_required:
            raise ValueError("Manual de onboarding IA externa exige tenant_scope_required=True.")
        if self.sql_freeform_allowed:
            raise ValueError("Manual de onboarding IA externa não pode liberar SQL livre.")
        surfaces = {rule.surface for rule in self.surface_access_rules}
        if not {"user", "admin", "analytics", "ops"}.issubset(surfaces):
            raise ValueError("Manual deve cobrir user, admin, analytics e ops.")
        phases = {step.phase for step in self.steps}
        if not {"intake", "access_design", "registration", "validation", "operation"}.issubset(phases):
            raise ValueError("Manual deve cobrir todas as fases de onboarding.")
        return self

    def get_surface_rule(self, surface: str) -> ExternalAISurfaceAccessRule | None:
        normalized = str(surface or "").strip().lower()
        for rule in self.surface_access_rules:
            if rule.surface == normalized:
                return rule
        return None


ExternalAIOnboardingEnvelope = MCPSuccessEnvelope[ExternalAIOnboardingManifest | ExternalAISurfaceAccessRule]


def build_external_ai_onboarding_manifest() -> ExternalAIOnboardingManifest:
    return ExternalAIOnboardingManifest(
        supported_provider_types=["chatgpt", "claude", "gemini", "custom_agent", "internal_agent"],
        required_global_discovery_tools=[
            "list_app32_capabilities",
            "describe_app32_profile_contracts_tool",
            "describe_app32_surface_playbooks_tool",
            "describe_app32_domain_playbooks_tool",
            "describe_app32_release_checklist_tool",
            "describe_app32_tool_freeze_procedure_tool",
        ],
        surface_access_rules=[
            ExternalAISurfaceAccessRule(
                surface="user",
                allowed_provider_types=["chatgpt", "claude", "gemini", "custom_agent", "internal_agent"],
                allowed_profiles=["colaborador", "cliente", "administrador"],
                required_discovery_tools=["list_user_app32_capabilities", "describe_app32_surface_playbooks_tool"],
            ),
            ExternalAISurfaceAccessRule(
                surface="admin",
                allowed_provider_types=["custom_agent", "internal_agent"],
                allowed_profiles=["administrador", "admin_tecnico"],
                required_discovery_tools=["list_admin_app32_capabilities", "describe_app32_profile_contracts_tool"],
            ),
            ExternalAISurfaceAccessRule(
                surface="analytics",
                allowed_provider_types=["custom_agent", "internal_agent"],
                allowed_profiles=["administrador", "admin_tecnico"],
                required_discovery_tools=["list_analytics_app32_capabilities", "describe_app32_allowed_analyses_tool"],
            ),
            ExternalAISurfaceAccessRule(
                surface="ops",
                allowed_provider_types=["internal_agent"],
                allowed_profiles=["admin_tecnico"],
                required_discovery_tools=["list_ops_app32_capabilities", "describe_app32_tool_freeze_procedure_tool"],
            ),
        ],
        steps=[
            ExternalAIOnboardingStep(
                step_id="intake_provider",
                phase="intake",
                title="Identificar IA externa e caso de uso",
                instruction="Registrar provider, finalidade, canal, usuário responsável, surface pretendida e domínios necessários.",
                required_evidence="Ficha de intake com provider, surface, perfil e company_id alvo.",
            ),
            ExternalAIOnboardingStep(
                step_id="access_profile",
                phase="access_design",
                title="Definir perfil e menor privilégio",
                instruction="Consultar contratos de perfil e surface antes de liberar qualquer tool MCP.",
                required_evidence="Perfil/surface aprovados e domínios permitidos documentados.",
            ),
            ExternalAIOnboardingStep(
                step_id="register_client",
                phase="registration",
                title="Registrar cliente/integração MCP",
                instruction="Configurar o cliente MCP sem expor segredos em prompt, logs ou metadata e com rotação planejada.",
                required_evidence="Registro da integração e política de segredo/rotação associada.",
            ),
            ExternalAIOnboardingStep(
                step_id="validate_smokes",
                phase="validation",
                title="Executar smokes de go-live",
                instruction="Executar capabilities, playbooks, release checklist e tool freeze antes de liberar operação assistida.",
                required_evidence="Smokes de go-live retornando marcadores *_OK esperados.",
            ),
            ExternalAIOnboardingStep(
                step_id="operate_monitor",
                phase="operation",
                title="Operar com monitoramento e congelamento",
                instruction="Monitorar auditoria IA/MCP e aplicar congelamento quando houver trigger crítico.",
                required_evidence="Dashboard/relatório de uso e procedimento de freeze disponíveis para suporte.",
            ),
        ],
        go_live_smokes=[
            "MCP_USER_ADMIN_RUNBOOK_SMOKE_OK True True",
            "AI_MCP_RELEASE_CHECKLIST_OK 7 3",
            "AI_MCP_TOOL_FREEZE_OK 7 4",
            "AI_MCP_EXTERNAL_ONBOARDING_OK 4 5",
        ],
        forbidden_patterns=[
            "Não liberar SQL livre para IA externa.",
            "Não compartilhar tokens, cookies, senhas ou chaves em prompt.",
            "Não conceder admin/ops a provider genérico sem aprovação humana.",
            "Não executar operação sem company_id explícito quando o contrato exigir.",
        ],
    )


APP32_EXTERNAL_AI_ONBOARDING_MANIFEST = build_external_ai_onboarding_manifest()


__all__ = [
    "APP32_EXTERNAL_AI_ONBOARDING_MANIFEST",
    "ExternalAIOnboardingEnvelope",
    "ExternalAIOnboardingManifest",
    "ExternalAIOnboardingPhase",
    "ExternalAIOnboardingStep",
    "ExternalAIProviderType",
    "ExternalAISurfaceAccessRule",
    "build_external_ai_onboarding_manifest",
]
