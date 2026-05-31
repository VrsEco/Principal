from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from .base import MCPSuccessEnvelope, _StrictModel
from .playbooks import APP32_SURFACE_PLAYBOOKS_MANIFEST, PlaybookSurface
from .profiles import APP32_PROFILE_CONTRACTS_MANIFEST, MCPMutationRisk, MCPOverlayName, MCPProfileName


PermissionAction = Literal["discover", "read", "create", "update", "delete", "analyze", "audit", "review"]
PermissionDomain = Literal[
    "routine",
    "processes",
    "projects",
    "meetings",
    "strategy",
    "real_estate_auctions",
    "finance",
    "governance",
    "analytics",
    "workload",
    "operations",
    "identity_self_service",
    "identity_admin",
]


class PermissionDomainRule(_StrictModel):
    domain: PermissionDomain
    allowed_actions: list[PermissionAction] = Field(default_factory=list, min_length=1)
    denied_actions: list[PermissionAction] = Field(default_factory=list)
    max_risk_without_human_gate: MCPMutationRisk = "medium"
    requires_explicit_company_id: bool = False
    human_gate_for_actions: list[PermissionAction] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list, min_length=1)

    @model_validator(mode="after")
    def _validate_rule(self):
        allowed = set(self.allowed_actions)
        denied = set(self.denied_actions)
        if allowed & denied:
            raise ValueError("Ações permitidas e negadas não podem se sobrepor na matriz.")
        if self.domain == "finance":
            if self.max_risk_without_human_gate not in {"low", "medium"}:
                raise ValueError("Matriz financeira deve declarar risco máximo sem gate como low/medium.")
            if not self.requires_explicit_company_id:
                raise ValueError("Domínio financeiro exige company_id explícito na matriz canônica.")
            if "delete" in allowed and "delete" not in set(self.human_gate_for_actions):
                raise ValueError("Delete financeiro deve exigir gate humano na matriz.")
        if self.domain == "analytics" and any(action in allowed for action in {"create", "update", "delete", "review"}):
            raise ValueError("Domínio analytics na matriz não pode liberar mutação.")
        if self.domain == "operations" and "audit" not in allowed:
            raise ValueError("Domínio operations deve manter trilha auditável explícita na matriz.")
        return self


class ProfilePermissionSurfaceMatrix(_StrictModel):
    profile: MCPProfileName
    surface: PlaybookSurface
    title: str = Field(min_length=8, max_length=160)
    summary: str = Field(min_length=16, max_length=360)
    domains: list[PermissionDomainRule] = Field(default_factory=list, min_length=1)
    default_scope: Literal["active_company", "explicit_company_id"] = "active_company"
    tenant_scope_required: bool = True
    sql_freeform_allowed: bool = False

    @model_validator(mode="after")
    def _validate_matrix(self):
        if not self.tenant_scope_required:
            raise ValueError("Matriz de permissões exige tenant_scope_required=True.")
        if self.sql_freeform_allowed:
            raise ValueError("Matriz de permissões não pode liberar SQL livre.")

        profile_contract = APP32_PROFILE_CONTRACTS_MANIFEST.get_profile(self.profile)
        if profile_contract is None:
            raise ValueError(f"Perfil não suportado na matriz: {self.profile}.")
        if self.surface not in profile_contract.allowed_surfaces:
            raise ValueError("Surface da matriz precisa existir no contrato do perfil.")

        playbook = APP32_SURFACE_PLAYBOOKS_MANIFEST.get_surface(self.surface)
        if playbook is None:
            raise ValueError(f"Surface playbook ausente para {self.surface}.")
        if self.default_scope != playbook.default_scope:
            raise ValueError("default_scope da matriz deve seguir o playbook da surface.")

        domains = [rule.domain for rule in self.domains]
        if len(domains) != len(set(domains)):
            raise ValueError("Domínio não pode se repetir na mesma matriz de profile/surface.")
        for rule in self.domains:
            if rule.domain not in set(profile_contract.allowed_domains):
                raise ValueError(f"Domínio {rule.domain} não permitido para o perfil {self.profile}.")
            if rule.domain not in set(playbook.allowed_domains):
                raise ValueError(f"Domínio {rule.domain} não permitido na surface {self.surface}.")
        if self.profile == "cliente":
            for rule in self.domains:
                if any(action in rule.allowed_actions for action in {"create", "update", "delete", "audit"}):
                    raise ValueError("Cliente não pode receber ações de mutação/auditoria na matriz.")
        if self.profile == "colaborador" and self.surface != "user":
            raise ValueError("Colaborador fica restrito à surface user na matriz.")
        if self.surface == "analytics":
            for rule in self.domains:
                if any(action in rule.allowed_actions for action in {"create", "update", "delete", "review"}):
                    raise ValueError("Surface analytics na matriz deve permanecer read-only.")
        if self.surface == "ops" and self.profile != "admin_tecnico":
            raise ValueError("Surface ops na matriz fica restrita ao admin_tecnico.")
        return self


class OverlayPermissionSurfaceMatrix(_StrictModel):
    overlay: MCPOverlayName
    runtime_profile: str = Field(min_length=3, max_length=80)
    surface: PlaybookSurface
    title: str = Field(min_length=8, max_length=160)
    summary: str = Field(min_length=16, max_length=360)
    compatible_profiles: list[MCPProfileName] = Field(default_factory=list, min_length=1)
    harness_keys: list[str] = Field(default_factory=list, min_length=1)
    domains: list[PermissionDomainRule] = Field(default_factory=list, min_length=1)
    default_scope: Literal["active_company", "explicit_company_id"] = "active_company"
    tenant_scope_required: bool = True

    @model_validator(mode="after")
    def _validate_overlay_matrix(self):
        if not self.tenant_scope_required:
            raise ValueError("Overlay matrix exige tenant_scope_required=True.")
        playbook = APP32_SURFACE_PLAYBOOKS_MANIFEST.get_surface(self.surface)
        if playbook is None:
            raise ValueError(f"Surface playbook ausente para {self.surface}.")
        if self.default_scope != playbook.default_scope:
            raise ValueError("default_scope do overlay matrix deve seguir o playbook da surface.")
        overlay_contract = APP32_PROFILE_CONTRACTS_MANIFEST.get_overlay(self.overlay)
        if overlay_contract is None:
            raise ValueError(f"Overlay não suportado na matriz: {self.overlay}.")
        if self.runtime_profile != overlay_contract.runtime_profile:
            raise ValueError("runtime_profile do overlay matrix deve seguir o contrato do overlay.")
        if self.surface != overlay_contract.surface:
            raise ValueError("surface do overlay matrix deve seguir o contrato do overlay.")
        if set(self.compatible_profiles) != set(overlay_contract.compatible_profiles):
            raise ValueError("compatible_profiles do overlay matrix deve seguir o contrato do overlay.")
        if set(self.harness_keys) != {overlay_contract.harness_key}:
            raise ValueError("harness_keys do overlay matrix deve seguir o contrato do overlay.")
        matrix_domains = {rule.domain for rule in self.domains}
        if matrix_domains != set(overlay_contract.allowed_domains):
            raise ValueError("Domínios do overlay matrix devem refletir exatamente os domínios permitidos no contrato do overlay.")
        for rule in self.domains:
            if any(action not in set(overlay_contract.allowed_actions) for action in rule.allowed_actions):
                raise ValueError("Overlay matrix não pode liberar ação fora do contrato do overlay.")
        return self


class PermissionMatrixManifest(_StrictModel):
    version: str = Field(default="app32.ai-mcp.permission-matrix.v1", min_length=1, max_length=80)
    matrices: list[ProfilePermissionSurfaceMatrix] = Field(default_factory=list, min_length=1)
    overlay_matrices: list[OverlayPermissionSurfaceMatrix] = Field(default_factory=list)

    def get_profile(self, profile: MCPProfileName | str) -> list[ProfilePermissionSurfaceMatrix]:
        normalized = str(profile or "").strip().lower()
        alias = "admin_tecnico" if normalized == "administrador_tecnico" else normalized
        return [matrix for matrix in self.matrices if matrix.profile == alias]

    def get_surface(self, surface: PlaybookSurface | str) -> list[ProfilePermissionSurfaceMatrix]:
        normalized = str(surface or "").strip().lower()
        return [matrix for matrix in self.matrices if matrix.surface == normalized]

    def get_overlay(self, overlay: MCPOverlayName | str) -> list[OverlayPermissionSurfaceMatrix]:
        normalized = str(overlay or "").strip().lower()
        return [matrix for matrix in self.overlay_matrices if matrix.overlay == normalized or normalized in set(matrix.harness_keys)]


PermissionMatrixEnvelope = MCPSuccessEnvelope[
    PermissionMatrixManifest | ProfilePermissionSurfaceMatrix | list[ProfilePermissionSurfaceMatrix]
]


def _rule(
    domain: PermissionDomain,
    allowed: list[PermissionAction],
    *,
    denied: list[PermissionAction] | None = None,
    max_risk_without_human_gate: MCPMutationRisk = "medium",
    requires_explicit_company_id: bool = False,
    human_gate_for_actions: list[PermissionAction] | None = None,
    notes: list[str] | None = None,
) -> PermissionDomainRule:
    return PermissionDomainRule(
        domain=domain,
        allowed_actions=allowed,
        denied_actions=denied or [],
        max_risk_without_human_gate=max_risk_without_human_gate,
        requires_explicit_company_id=requires_explicit_company_id,
        human_gate_for_actions=human_gate_for_actions or [],
        notes=notes or ["Seguir contratos MCP e policy engine como fonte de decisão final."],
    )


def build_permission_matrix_manifest() -> PermissionMatrixManifest:
    return PermissionMatrixManifest(
        overlay_matrices=[
            OverlayPermissionSurfaceMatrix(
                overlay="coordenador_versus",
                runtime_profile="squad_versus",
                surface="admin",
                title="Overlay Matrix — Coordenador do Squad Versus",
                summary="Discovery consultivo e roteamento metodológico com leitura ampla e atualização controlada.",
                compatible_profiles=["administrador"],
                harness_keys=["harness_coordenador_versus_v1"],
                default_scope="explicit_company_id",
                domains=[
                    _rule("routine", ["discover", "read", "analyze", "update"], requires_explicit_company_id=True, notes=["Leitura consultiva de rotina."]),
                    _rule("processes", ["discover", "read", "analyze", "update"], requires_explicit_company_id=True, notes=["Estruturação de processos e intervenção consultiva."]),
                    _rule("projects", ["discover", "read", "analyze", "update"], requires_explicit_company_id=True, notes=["Projetos em modo consultivo."]),
                    _rule("meetings", ["discover", "read", "analyze", "update"], requires_explicit_company_id=True, notes=["Reuniões e follow-up executivo."]),
                    _rule("strategy", ["discover", "read", "analyze", "update"], requires_explicit_company_id=True, human_gate_for_actions=["update"], notes=["Estratégia com mutação consultiva controlada."]),
                    _rule("governance", ["discover", "read", "analyze", "update"], requires_explicit_company_id=True, human_gate_for_actions=["update"], notes=["Governança consultiva."]),
                    _rule("finance", ["discover", "read", "analyze", "update"], requires_explicit_company_id=True, human_gate_for_actions=["update"], notes=["Finanças com leitura controlada e update sob gate."]),
                ],
            ),
            OverlayPermissionSurfaceMatrix(
                overlay="strategist_versus",
                runtime_profile="squad_versus",
                surface="admin",
                title="Overlay Matrix — Strategist Versus",
                summary="Especialista de estratégia e crescimento com foco em análise e evolução controlada de planos.",
                compatible_profiles=["administrador"],
                harness_keys=["harness_strategist_versus_v1"],
                default_scope="explicit_company_id",
                domains=[
                    _rule("strategy", ["discover", "read", "analyze", "update"], requires_explicit_company_id=True, human_gate_for_actions=["update"], notes=["Planos e indicadores em modo consultivo."]),
                    _rule("projects", ["discover", "read", "analyze"], requires_explicit_company_id=True, notes=["Projetos como evidência estratégica."]),
                    _rule("meetings", ["discover", "read", "analyze"], requires_explicit_company_id=True, notes=["Reuniões estratégicas e follow-up executivo."]),
                    _rule("governance", ["discover", "read", "analyze"], requires_explicit_company_id=True, notes=["Governança em leitura crítica."]),
                ],
            ),
            OverlayPermissionSurfaceMatrix(
                overlay="pmo_controller_versus",
                runtime_profile="squad_versus",
                surface="admin",
                title="Overlay Matrix — PMO Controller Versus",
                summary="Cadência, governança de execução e cobrança estruturada de andamento.",
                compatible_profiles=["administrador"],
                harness_keys=["harness_pmo_controller_versus_v1"],
                default_scope="explicit_company_id",
                domains=[
                    _rule("routine", ["discover", "read", "analyze", "update"], requires_explicit_company_id=True, notes=["Cadência operacional."]),
                    _rule("processes", ["discover", "read", "analyze", "update"], requires_explicit_company_id=True, notes=["Acompanhamento de execução de processos."]),
                    _rule("projects", ["discover", "read", "analyze", "update"], requires_explicit_company_id=True, notes=["PMO sobre projetos e tarefas."]),
                    _rule("meetings", ["discover", "read", "analyze", "update"], requires_explicit_company_id=True, notes=["Ritos executivos e follow-up."]),
                    _rule("strategy", ["discover", "read", "analyze"], requires_explicit_company_id=True, notes=["Leitura de direção estratégica."]),
                    _rule("governance", ["discover", "read", "analyze", "update"], requires_explicit_company_id=True, human_gate_for_actions=["update"], notes=["Governança de execução."]),
                ],
            ),
            OverlayPermissionSurfaceMatrix(
                overlay="business_architect_versus",
                runtime_profile="squad_versus",
                surface="admin",
                title="Overlay Matrix — Business Architect Versus",
                summary="Desenho operacional, processos e coerência entre método, workflow e capability.",
                compatible_profiles=["administrador"],
                harness_keys=["harness_business_architect_versus_v1"],
                default_scope="explicit_company_id",
                domains=[
                    _rule("routine", ["discover", "read", "analyze"], requires_explicit_company_id=True, notes=["Rotina como insumo arquitetural."]),
                    _rule("processes", ["discover", "read", "analyze", "update"], requires_explicit_company_id=True, human_gate_for_actions=["update"], notes=["Processos e desenho operacional."]),
                    _rule("projects", ["discover", "read", "analyze"], requires_explicit_company_id=True, notes=["Projetos como evidência de execução."]),
                    _rule("meetings", ["discover", "read", "analyze"], requires_explicit_company_id=True, notes=["Reuniões como fonte de contexto."]),
                    _rule("strategy", ["discover", "read", "analyze"], requires_explicit_company_id=True, notes=["Estratégia como norte de desenho."]),
                    _rule("governance", ["discover", "read", "analyze", "update"], requires_explicit_company_id=True, human_gate_for_actions=["update"], notes=["Governança estrutural."]),
                ],
            ),
            OverlayPermissionSurfaceMatrix(
                overlay="operations_versus",
                runtime_profile="squad_versus",
                surface="admin",
                title="Overlay Matrix — Operations Versus",
                summary="Leitura crítica da operação com orientação consultiva e ajustes controlados.",
                compatible_profiles=["administrador"],
                harness_keys=["harness_operations_versus_v1"],
                default_scope="explicit_company_id",
                domains=[
                    _rule("routine", ["discover", "read", "analyze", "update"], requires_explicit_company_id=True, notes=["Rotina operacional."]),
                    _rule("processes", ["discover", "read", "analyze", "update"], requires_explicit_company_id=True, notes=["Processos operacionais."]),
                    _rule("projects", ["discover", "read", "analyze", "update"], requires_explicit_company_id=True, notes=["Projetos de execução."]),
                    _rule("meetings", ["discover", "read", "analyze", "update"], requires_explicit_company_id=True, notes=["Reuniões de operação."]),
                    _rule("strategy", ["discover", "read", "analyze"], requires_explicit_company_id=True, notes=["Leitura de alinhamento estratégico."]),
                ],
            ),
            OverlayPermissionSurfaceMatrix(
                overlay="followup_collector_versus",
                runtime_profile="squad_versus",
                surface="admin",
                title="Overlay Matrix — Follow-up Collector Versus",
                summary="Cobrança estruturada, fechamento de pendências e manutenção da cadência consultiva.",
                compatible_profiles=["administrador"],
                harness_keys=["harness_followup_collector_versus_v1"],
                default_scope="explicit_company_id",
                domains=[
                    _rule("routine", ["discover", "read", "analyze", "update"], requires_explicit_company_id=True, notes=["Pendências e follow-up de rotina."]),
                    _rule("projects", ["discover", "read", "analyze", "update"], requires_explicit_company_id=True, notes=["Pendências de projeto."]),
                    _rule("meetings", ["discover", "read", "analyze", "update"], requires_explicit_company_id=True, notes=["Pendências de reunião."]),
                    _rule("governance", ["discover", "read", "analyze"], requires_explicit_company_id=True, notes=["Governança da cadência."]),
                ],
            ),
            OverlayPermissionSurfaceMatrix(
                overlay="performance_analyst_versus",
                runtime_profile="squad_versus",
                surface="analytics",
                title="Overlay Matrix — Performance Analyst Versus",
                summary="Análise executiva de performance e indicadores em modo estritamente read-only.",
                compatible_profiles=["administrador"],
                harness_keys=["harness_performance_analyst_versus_v1"],
                default_scope="explicit_company_id",
                domains=[
                    _rule("analytics", ["discover", "read", "analyze"], denied=["create", "update", "delete", "audit"], requires_explicit_company_id=True, notes=["Read-only analítico."]),
                    _rule("strategy", ["discover", "read", "analyze"], denied=["create", "update", "delete", "audit"], requires_explicit_company_id=True, notes=["Indicadores e planos."]),
                    _rule("workload", ["discover", "read", "analyze"], denied=["create", "update", "delete", "audit"], requires_explicit_company_id=True, notes=["Capacidade e sinais executivos."]),
                ],
            ),
            OverlayPermissionSurfaceMatrix(
                overlay="finance_versus",
                runtime_profile="squad_versus",
                surface="admin",
                title="Overlay Matrix — Finance Versus",
                summary="Controladoria e crítica econômico-financeira com leitura forte e update controlado.",
                compatible_profiles=["administrador"],
                harness_keys=["harness_finance_versus_v1"],
                default_scope="explicit_company_id",
                domains=[
                    _rule("finance", ["discover", "read", "analyze", "update"], requires_explicit_company_id=True, human_gate_for_actions=["update"], notes=["Finanças com gate em mutação."]),
                    _rule("strategy", ["discover", "read", "analyze"], requires_explicit_company_id=True, notes=["Estratégia econômico-financeira."]),
                    _rule("governance", ["discover", "read", "analyze"], requires_explicit_company_id=True, notes=["Governança de controladoria."]),
                ],
            ),
            OverlayPermissionSurfaceMatrix(
                overlay="auditor_versus",
                runtime_profile="squad_versus",
                surface="analytics",
                title="Overlay Matrix — Auditor Versus",
                summary="Auditoria em modo read-only com foco em conformidade, finanças e execução.",
                compatible_profiles=["administrador"],
                harness_keys=["harness_auditor_versus_v1"],
                default_scope="explicit_company_id",
                domains=[
                    _rule("analytics", ["discover", "read", "analyze", "audit"], denied=["create", "update", "delete"], requires_explicit_company_id=True, notes=["Read-only auditável."]),
                    _rule("finance", ["discover", "read", "analyze", "audit"], denied=["create", "update", "delete"], requires_explicit_company_id=True, human_gate_for_actions=["analyze"], notes=["Leitura financeira auditável."]),
                    _rule("strategy", ["discover", "read", "analyze", "audit"], denied=["create", "update", "delete"], requires_explicit_company_id=True, notes=["Leitura estratégica auditável."]),
                    _rule("governance", ["discover", "read", "analyze", "audit"], denied=["create", "update", "delete"], requires_explicit_company_id=True, notes=["Conformidade e governança."]),
                    _rule("workload", ["discover", "read", "analyze", "audit"], denied=["create", "update", "delete"], requires_explicit_company_id=True, notes=["Capacidade em leitura auditável."]),
                ],
            ),
            OverlayPermissionSurfaceMatrix(
                overlay="coordenador_engenharia",
                runtime_profile="engineering",
                surface="ops",
                title="Overlay Matrix — Coordenador do Squad de Engenharia",
                summary="Triagem técnica e roteamento disciplinado em ops com visão transversal de intervenção.",
                compatible_profiles=["admin_tecnico"],
                harness_keys=["harness_coordenador_engenharia_v1"],
                default_scope="active_company",
                domains=[
                    _rule("operations", ["discover", "read", "analyze", "audit", "update"], human_gate_for_actions=["update"], notes=["Coordenação de incidente/intervenção."]),
                    _rule("routine", ["discover", "read", "analyze", "audit", "update"], human_gate_for_actions=["update"], notes=["Rotina em contexto técnico."]),
                    _rule("processes", ["discover", "read", "analyze", "audit", "update"], human_gate_for_actions=["update"], notes=["Processos em contexto técnico."]),
                    _rule("projects", ["discover", "read", "analyze", "audit", "update"], human_gate_for_actions=["update"], notes=["Projetos em contexto técnico."]),
                    _rule("meetings", ["discover", "read", "analyze", "audit", "update"], human_gate_for_actions=["update"], notes=["Reuniões em contexto técnico."]),
                    _rule("workload", ["discover", "read", "analyze"], notes=["Capacidade técnica."]),
                    _rule("governance", ["discover", "read", "analyze", "audit"], notes=["Governança técnica."]),
                ],
            ),
            OverlayPermissionSurfaceMatrix(
                overlay="arquiteto_engenharia",
                runtime_profile="engineering",
                surface="admin",
                title="Overlay Matrix — Arquiteto de Engenharia",
                summary="Boundary, segurança, arquitetura e coerência estrutural.",
                compatible_profiles=["admin_tecnico"],
                harness_keys=["harness_arquiteto_engenharia_v1"],
                default_scope="explicit_company_id",
                domains=[
                    _rule("governance", ["discover", "read", "analyze", "audit", "update"], requires_explicit_company_id=True, human_gate_for_actions=["update"], notes=["Governança e boundary."]),
                    _rule("strategy", ["discover", "read", "analyze"], requires_explicit_company_id=True, notes=["Estratégia técnica."]),
                    _rule("identity_admin", ["discover", "read", "analyze", "audit", "update"], requires_explicit_company_id=True, human_gate_for_actions=["update"], notes=["Admin técnico de identidade."]),
                    _rule("analytics", ["discover", "read", "analyze"], requires_explicit_company_id=True, notes=["Diagnóstico complementar."]),
                ],
            ),
            OverlayPermissionSurfaceMatrix(
                overlay="frontend_engenharia",
                runtime_profile="engineering",
                surface="ops",
                title="Overlay Matrix — Frontend de Engenharia",
                summary="Diagnóstico e ajuste técnico de interface, UX e templates.",
                compatible_profiles=["admin_tecnico"],
                harness_keys=["harness_frontend_engenharia_v1"],
                default_scope="active_company",
                domains=[
                    _rule("operations", ["discover", "read", "analyze", "audit", "update"], human_gate_for_actions=["update"], notes=["Incidente/ajuste de interface."]),
                    _rule("routine", ["discover", "read", "analyze", "audit", "update"], notes=["Fluxos operacionais em UI."]),
                    _rule("projects", ["discover", "read", "analyze", "audit", "update"], notes=["Projetos/telas."]),
                    _rule("meetings", ["discover", "read", "analyze", "audit", "update"], notes=["Reuniões/telas."]),
                ],
            ),
            OverlayPermissionSurfaceMatrix(
                overlay="backend_api_engenharia",
                runtime_profile="engineering",
                surface="admin",
                title="Overlay Matrix — Backend API de Engenharia",
                summary="Contratos, surfaces, schemas e publicação coerente de capabilities.",
                compatible_profiles=["admin_tecnico"],
                harness_keys=["harness_backend_api_engenharia_v1"],
                default_scope="explicit_company_id",
                domains=[
                    _rule("governance", ["discover", "read", "analyze", "audit", "update"], requires_explicit_company_id=True, human_gate_for_actions=["update"], notes=["Governança de contracts/surfaces."]),
                    _rule("identity_admin", ["discover", "read", "analyze", "audit", "update"], requires_explicit_company_id=True, human_gate_for_actions=["update"], notes=["Identity admin técnico."]),
                    _rule("analytics", ["discover", "read", "analyze"], requires_explicit_company_id=True, notes=["Diagnóstico complementar."]),
                    _rule("strategy", ["discover", "read", "analyze"], requires_explicit_company_id=True, notes=["Readiness técnica."]),
                ],
            ),
            OverlayPermissionSurfaceMatrix(
                overlay="backend_service_engenharia",
                runtime_profile="engineering",
                surface="ops",
                title="Overlay Matrix — Backend Service de Engenharia",
                summary="Regra de negócio determinística e services reutilizáveis em contexto de intervenção técnica.",
                compatible_profiles=["admin_tecnico"],
                harness_keys=["harness_backend_service_engenharia_v1"],
                default_scope="active_company",
                domains=[
                    _rule("operations", ["discover", "read", "analyze", "audit", "update"], human_gate_for_actions=["update"], notes=["Intervenção service-side."]),
                    _rule("routine", ["discover", "read", "analyze", "audit", "update"], notes=["Rotina em contexto técnico."]),
                    _rule("processes", ["discover", "read", "analyze", "audit", "update"], notes=["Processos em contexto técnico."]),
                    _rule("projects", ["discover", "read", "analyze", "audit", "update"], notes=["Projetos em contexto técnico."]),
                    _rule("meetings", ["discover", "read", "analyze", "audit", "update"], notes=["Meetings em contexto técnico."]),
                    _rule("governance", ["discover", "read", "analyze", "audit"], notes=["Coerência de service."]),
                ],
            ),
            OverlayPermissionSurfaceMatrix(
                overlay="ai_engineer_engenharia",
                runtime_profile="engineering",
                surface="admin",
                title="Overlay Matrix — AI Engineer de Engenharia",
                summary="Agentes, MCP, LangGraph, RAG e orquestração inteligente com governança.",
                compatible_profiles=["admin_tecnico"],
                harness_keys=["harness_ai_engineer_engenharia_v1"],
                default_scope="explicit_company_id",
                domains=[
                    _rule("governance", ["discover", "read", "analyze", "audit", "update"], requires_explicit_company_id=True, human_gate_for_actions=["update"], notes=["Governança agentic/MCP."]),
                    _rule("analytics", ["discover", "read", "analyze"], requires_explicit_company_id=True, notes=["Diagnóstico de telemetria e uso."]),
                    _rule("strategy", ["discover", "read", "analyze"], requires_explicit_company_id=True, notes=["Evolução de capabilities."]),
                    _rule("identity_admin", ["discover", "read", "analyze"], requires_explicit_company_id=True, notes=["Identidade técnica quando estritamente necessário."]),
                ],
            ),
            OverlayPermissionSurfaceMatrix(
                overlay="dba_engenharia",
                runtime_profile="engineering",
                surface="analytics",
                title="Overlay Matrix — DBA de Engenharia",
                summary="Diagnóstico de dados, performance e integridade em modo read-only e auditável.",
                compatible_profiles=["admin_tecnico"],
                harness_keys=["harness_dba_engenharia_v1"],
                default_scope="explicit_company_id",
                domains=[
                    _rule("analytics", ["discover", "read", "analyze", "audit"], denied=["create", "update", "delete"], requires_explicit_company_id=True, notes=["Diagnóstico de dados read-only."]),
                    _rule("workload", ["discover", "read", "analyze", "audit"], denied=["create", "update", "delete"], requires_explicit_company_id=True, notes=["Capacidade e performance."]),
                    _rule("governance", ["discover", "read", "analyze", "audit"], denied=["create", "update", "delete"], requires_explicit_company_id=True, notes=["Governança de dados."]),
                    _rule("strategy", ["discover", "read", "analyze"], denied=["create", "update", "delete"], requires_explicit_company_id=True, notes=["Readiness técnica."]),
                ],
            ),
            OverlayPermissionSurfaceMatrix(
                overlay="qa_automation_engenharia",
                runtime_profile="engineering",
                surface="ops",
                title="Overlay Matrix — QA Automation de Engenharia",
                summary="Smoke, regressão, evidência e validação disciplinada em contexto técnico.",
                compatible_profiles=["admin_tecnico"],
                harness_keys=["harness_qa_automation_engenharia_v1"],
                default_scope="active_company",
                domains=[
                    _rule("operations", ["discover", "read", "analyze", "audit", "update"], human_gate_for_actions=["update"], notes=["Validação técnica em incidente/intervenção."]),
                    _rule("routine", ["discover", "read", "analyze", "audit", "update"], notes=["Smoke de fluxos operacionais."]),
                    _rule("processes", ["discover", "read", "analyze", "audit", "update"], notes=["Regressão de processos."]),
                    _rule("projects", ["discover", "read", "analyze", "audit", "update"], notes=["Regressão de projetos/tarefas."]),
                    _rule("meetings", ["discover", "read", "analyze", "audit", "update"], notes=["Regressão de reuniões."]),
                    _rule("workload", ["discover", "read", "analyze"], notes=["Indicadores de capacidade técnica."]),
                    _rule("governance", ["discover", "read", "analyze", "audit"], notes=["Evidência e critérios de aceite."]),
                ],
            ),
            OverlayPermissionSurfaceMatrix(
                overlay="coordenador_cliente",
                runtime_profile="squad_cliente",
                surface="user",
                title="Overlay Matrix — Coordenador do Squad Cliente",
                summary="Roteamento inicial e visão transversal do Squad Cliente, com criação/atualização operacional e bloqueio de domínios sensíveis.",
                compatible_profiles=["cliente", "colaborador", "administrador"],
                harness_keys=["harness_coordenador_cliente_v1"],
                default_scope="active_company",
                domains=[
                    _rule("routine", ["discover", "read", "create", "update"], denied=["delete", "audit"], notes=["Coordenação operacional do dia a dia."]),
                    _rule("processes", ["discover", "read", "create", "update"], denied=["delete", "audit"], notes=["Pode estruturar execução de processos na surface user."]),
                    _rule("projects", ["discover", "read", "create", "update"], denied=["delete", "audit"], notes=["Coordena tarefas e projetos do cliente."]),
                    _rule("meetings", ["discover", "read", "create", "update"], denied=["delete", "audit"], notes=["Coordena reuniões e follow-up do cliente."]),
                    _rule("strategy", ["discover", "read", "analyze"], denied=["create", "update", "delete", "audit"], notes=["Estratégia em leitura/análise guiada."]),
                    _rule("identity_self_service", ["discover", "read"], denied=["create", "update", "delete", "audit"], notes=["Self-service só para contexto do próprio usuário."]),
                ],
            ),
            OverlayPermissionSurfaceMatrix(
                overlay="comercial_cliente",
                runtime_profile="squad_cliente",
                surface="user",
                title="Overlay Matrix — Comercial do Squad Cliente",
                summary="Foco comercial e de crescimento com atuação em rotina, projetos, reuniões e estratégia em menor privilégio.",
                compatible_profiles=["cliente", "colaborador", "administrador"],
                harness_keys=["harness_comercial_cliente_v1"],
                default_scope="active_company",
                domains=[
                    _rule("routine", ["discover", "read", "create", "update"], denied=["delete", "audit"], notes=["Cadência comercial e tarefas do relacionamento."]),
                    _rule("projects", ["discover", "read", "create", "update"], denied=["delete", "audit"], notes=["Pipeline e iniciativas comerciais assistidas."]),
                    _rule("meetings", ["discover", "read", "create", "update"], denied=["delete", "audit"], notes=["Reuniões comerciais e follow-up."]),
                    _rule("strategy", ["discover", "read", "analyze"], denied=["create", "update", "delete", "audit"], notes=["Leitura estratégica comercial, sem mutação estrutural."]),
                    _rule("identity_self_service", ["discover", "read"], denied=["create", "update", "delete", "audit"], notes=["Consulta de contexto próprio."]),
                ],
            ),
            OverlayPermissionSurfaceMatrix(
                overlay="operacional_cliente",
                runtime_profile="squad_cliente",
                surface="user",
                title="Overlay Matrix — Operacional do Squad Cliente",
                summary="Foco na execução operacional diária com permissão para criação/atualização em rotina, processos, projetos e reuniões.",
                compatible_profiles=["cliente", "colaborador", "administrador"],
                harness_keys=["harness_operacional_cliente_v1"],
                default_scope="active_company",
                domains=[
                    _rule("routine", ["discover", "read", "create", "update"], denied=["delete", "audit"], notes=["Execução operacional do dia a dia."]),
                    _rule("processes", ["discover", "read", "create", "update"], denied=["delete", "audit"], notes=["Condução de processos operacionais."]),
                    _rule("projects", ["discover", "read", "create", "update"], denied=["delete", "audit"], notes=["Acompanhamento e ajuste de tarefas."]),
                    _rule("meetings", ["discover", "read", "create", "update"], denied=["delete", "audit"], notes=["Coordenação operacional de reuniões."]),
                    _rule("identity_self_service", ["discover", "read"], denied=["create", "update", "delete", "audit"], notes=["Consulta de contexto próprio."]),
                ],
            ),
            OverlayPermissionSurfaceMatrix(
                overlay="admfin_cliente",
                runtime_profile="squad_cliente",
                surface="user",
                title="Overlay Matrix — Adm/Financeiro do Squad Cliente",
                summary="Organiza contexto administrativo/financeiro em modo permission-aware, operando apenas o que a senha do usuário já libera no APP32.",
                compatible_profiles=["cliente", "colaborador", "administrador"],
                harness_keys=["harness_admfin_cliente_v1"],
                default_scope="active_company",
                domains=[
                    _rule("routine", ["discover", "read", "create", "update"], denied=["delete", "audit"], max_risk_without_human_gate="medium", notes=["Consulta e organização operacional administrativa."]),
                    _rule("projects", ["discover", "read", "create", "update"], denied=["delete", "audit"], max_risk_without_human_gate="medium", notes=["Projetos com apoio administrativo contextual."]),
                    _rule("meetings", ["discover", "read", "create", "update"], denied=["delete", "audit"], max_risk_without_human_gate="medium", notes=["Reuniões em apoio administrativo e follow-up."]),
                    _rule("strategy", ["discover", "read", "create", "update", "analyze"], denied=["delete", "audit"], max_risk_without_human_gate="medium", notes=["Estratégia contextual ligada à operação administrativa."]),
                    _rule("finance", ["discover", "read", "create", "update", "analyze"], denied=["delete", "audit"], requires_explicit_company_id=True, max_risk_without_human_gate="medium", notes=["Financeiro permission-aware: só expor e executar o que a senha do usuário já permite no APP32."]),
                    _rule("identity_self_service", ["discover", "read", "create", "update"], denied=["delete", "audit"], notes=["Consulta e atualização do contexto próprio."]),
                ],
            ),
            OverlayPermissionSurfaceMatrix(
                overlay="estrategico_cliente",
                runtime_profile="squad_cliente",
                surface="user",
                title="Overlay Matrix — Estratégico do Squad Cliente",
                summary="Prioriza planos e sinais executivos em leitura/análise, sem mutação estrutural na surface user.",
                compatible_profiles=["cliente", "colaborador", "administrador"],
                harness_keys=["harness_estrategico_cliente_v1"],
                default_scope="active_company",
                domains=[
                    _rule("strategy", ["discover", "read", "analyze"], denied=["create", "update", "delete", "audit"], notes=["Diagnóstico e síntese estratégica assistida."]),
                    _rule("projects", ["discover", "read"], denied=["create", "update", "delete", "audit"], notes=["Projetos como evidência de execução."]),
                    _rule("meetings", ["discover", "read"], denied=["create", "update", "delete", "audit"], notes=["Reuniões estratégicas em leitura."]),
                    _rule("identity_self_service", ["discover", "read"], denied=["create", "update", "delete", "audit"], notes=["Consulta de contexto próprio."]),
                ],
            ),
            OverlayPermissionSurfaceMatrix(
                overlay="pessoas_capacidade_cliente",
                runtime_profile="squad_cliente",
                surface="user",
                title="Overlay Matrix — Pessoas/Capacidade do Squad Cliente",
                summary="Coordena pessoas e capacidade no plano operacional sem abrir analytics/workload privilegiado na surface user.",
                compatible_profiles=["cliente", "colaborador", "administrador"],
                harness_keys=["harness_pessoas_capacidade_cliente_v1"],
                default_scope="active_company",
                domains=[
                    _rule("routine", ["discover", "read", "create", "update"], denied=["delete", "audit"], notes=["Rotinas e tarefas da equipe."]),
                    _rule("projects", ["discover", "read", "create", "update"], denied=["delete", "audit"], notes=["Projetos e distribuição operacional do trabalho."]),
                    _rule("meetings", ["discover", "read", "create", "update"], denied=["delete", "audit"], notes=["Ritos e acompanhamentos da equipe."]),
                    _rule("identity_self_service", ["discover", "read"], denied=["create", "update", "delete", "audit"], notes=["Consulta de contexto próprio."]),
                ],
            ),
        ],
        matrices=[
            ProfilePermissionSurfaceMatrix(
                profile="colaborador",
                surface="user",
                title="Matriz de permissões MCP - Colaborador / User",
                summary="Colaborador atua na surface user com foco operacional e pode receber tools financeiras permission-aware quando a senha já libera a mesma ação no APP32.",
                default_scope="active_company",
                domains=[
                    _rule("routine", ["discover", "read", "create", "update"], denied=["delete", "audit"], notes=["Pode operar rotina do tenant ativo sem bypass de escopo."]),
                    _rule("processes", ["discover", "read", "create", "update"], denied=["delete", "audit"], notes=["Processos estruturados seguem surface user com rastreabilidade operacional."]),
                    _rule("projects", ["discover", "read", "create", "update"], denied=["delete", "audit"], notes=["Projetos e tarefas seguem surface user e trilha auditável do sistema."]),
                    _rule("meetings", ["discover", "read", "create", "update"], denied=["delete", "audit"], notes=["Reuniões permitem preparação e atualização operacional."]),
                    _rule("strategy", ["discover", "read", "analyze", "review"], denied=["create", "update", "delete", "audit"], human_gate_for_actions=["review"], notes=["Estratégia para colaborador fica restrita à leitura, análise assistida e revisão human-gate de maturação S1-S2."]),
                    _rule("real_estate_auctions", ["discover", "read", "create", "update"], denied=["delete", "audit"], notes=["Leilões imobiliários seguem tenant ativo e gate das tools em mutações."]),
                    _rule("finance", ["discover", "read", "create", "update"], denied=["delete", "audit"], requires_explicit_company_id=True, notes=["Financeiro na surface user é permission-aware: só aparece quando a senha do colaborador já possui a permissão web equivalente no APP32."]),
                ],
            ),
            ProfilePermissionSurfaceMatrix(
                profile="cliente",
                surface="user",
                title="Matriz de permissões MCP - Cliente / User",
                summary="Cliente atua apenas na surface user, com leitura guiada e revisão human-gate de maturação estratégica sem mutações operacionais ou administrativas amplas.",
                default_scope="active_company",
                domains=[
                    _rule("routine", ["discover", "read"], denied=["create", "update", "delete", "audit"], max_risk_without_human_gate="low", notes=["Cliente consulta rotinas sem alterar dados."]),
                    _rule("processes", ["discover", "read"], denied=["create", "update", "delete", "audit"], max_risk_without_human_gate="low", notes=["Cliente consulta processos em modo leitura, sem mutação."]),
                    _rule("projects", ["discover", "read"], denied=["create", "update", "delete", "audit"], max_risk_without_human_gate="low", notes=["Projetos do cliente são somente leitura."]),
                    _rule("meetings", ["discover", "read"], denied=["create", "update", "delete", "audit"], max_risk_without_human_gate="low", notes=["Acesso a reuniões é informativo, sem mutação."]),
                    _rule("strategy", ["discover", "read", "analyze", "review"], denied=["create", "update", "delete", "audit"], max_risk_without_human_gate="low", human_gate_for_actions=["review"], notes=["Cliente consulta diagnóstico estratégico e revisa maturação S1-S2 por human-gate, sem update estratégico genérico."]),
                    _rule("real_estate_auctions", ["discover", "read", "analyze"], denied=["create", "update", "delete", "audit"], max_risk_without_human_gate="low", notes=["Cliente consulta pipeline de leilões sem mutação via surface user."]),
                ],
            ),
            ProfilePermissionSurfaceMatrix(
                profile="administrador",
                surface="user",
                title="Matriz de permissões MCP - Administrador / User",
                summary="Administrador também pode operar pela surface user quando o fluxo for funcional e não exigir privilégios exclusivos de admin/analytics.",
                default_scope="active_company",
                domains=[
                    _rule("routine", ["discover", "read", "create", "update", "analyze"], denied=["delete"], notes=["Mutações destrutivas devem migrar para admin com confirmação."]),
                    _rule("processes", ["discover", "read", "create", "update", "analyze"], denied=["delete"], notes=["Processos operacionais podem ser geridos na surface user sem admin global."]),
                    _rule("projects", ["discover", "read", "create", "update", "analyze"], denied=["delete"], notes=["Projetos operacionais podem ser geridos na surface user."]),
                    _rule("meetings", ["discover", "read", "create", "update", "analyze"], denied=["delete"], notes=["Reuniões seguem fluxo operacional comum."]),
                    _rule("strategy", ["discover", "read", "create", "update", "analyze", "review"], denied=["delete"], human_gate_for_actions=["review"], notes=["Mudanças estratégicas sensíveis podem exigir redirecionamento para admin; revisão de maturação S1-S2 mantém human-gate."]),
                    _rule("real_estate_auctions", ["discover", "read", "create", "update", "analyze"], denied=["delete"], notes=["Admin pode operar o módulo de leilões pela surface user sem exclusões."]),
                    _rule("finance", ["discover", "read", "create", "update", "analyze"], denied=["delete"], requires_explicit_company_id=True, notes=["Administrador pode operar finanças pela surface user quando o fluxo funcional bastar e a permissão web equivalente estiver presente."]),
                ],
            ),
            ProfilePermissionSurfaceMatrix(
                profile="administrador",
                surface="admin",
                title="Matriz de permissões MCP - Administrador / Admin",
                summary="Administrador usa a surface admin para governança, mutações sensíveis e operações multiempresa com company_id explícito.",
                default_scope="explicit_company_id",
                domains=[
                    _rule("routine", ["discover", "read", "create", "update", "delete", "audit"], human_gate_for_actions=["delete"], requires_explicit_company_id=True, notes=["Delete requer confirmação explícita."]),
                    _rule("processes", ["discover", "read", "create", "update", "delete", "audit"], human_gate_for_actions=["delete"], requires_explicit_company_id=True, notes=["Processos sensíveis exigem confirmação em exclusão e escopo explícito."]),
                    _rule("projects", ["discover", "read", "create", "update", "delete", "audit"], human_gate_for_actions=["delete"], requires_explicit_company_id=True, notes=["Projetos sensíveis pedem gate em exclusão."]),
                    _rule("meetings", ["discover", "read", "create", "update", "delete", "audit"], human_gate_for_actions=["delete"], requires_explicit_company_id=True, notes=["Exclusão de reunião deve ser excepcional e auditada."]),
                    _rule("strategy", ["discover", "read", "create", "update", "delete", "analyze", "audit", "review"], human_gate_for_actions=["delete", "update", "review"], requires_explicit_company_id=True, notes=["Mudanças estratégicas relevantes pedem confirmação humana; revisão de maturação S1-S2 mantém gate específico."]),
                    _rule("real_estate_auctions", ["discover", "read", "create", "update", "delete", "analyze", "audit"], human_gate_for_actions=["create", "update", "delete"], requires_explicit_company_id=True, notes=["Módulo de leilões exige company_id explícito e gate humano em mutações sensíveis."]),
                    _rule("finance", ["discover", "read", "create", "update", "delete", "analyze", "audit"], denied=[], max_risk_without_human_gate="medium", requires_explicit_company_id=True, human_gate_for_actions=["create", "update", "delete"], notes=["Finanças exigem menor privilégio, company_id explícito e gate humano em mutações."]),
                    _rule("governance", ["discover", "read", "create", "update", "delete", "audit"], human_gate_for_actions=["delete", "update"], requires_explicit_company_id=True, notes=["Governança/admin deve preservar trilha de auditoria."]),
                ],
            ),
            ProfilePermissionSurfaceMatrix(
                profile="administrador",
                surface="analytics",
                title="Matriz de permissões MCP - Administrador / Analytics",
                summary="Administrador usa analytics para leitura, diagnóstico e cruzamento permitido, sem mutar dados operacionais.",
                default_scope="explicit_company_id",
                domains=[
                    _rule("analytics", ["discover", "read", "analyze"], denied=["create", "update", "delete", "audit"], requires_explicit_company_id=True, notes=["Analytics é estritamente read-only."]),
                    _rule("strategy", ["discover", "read", "analyze"], denied=["create", "update", "delete", "audit"], requires_explicit_company_id=True, notes=["Estratégia analítica usa read models whitelisted."]),
                    _rule("real_estate_auctions", ["discover", "read", "analyze"], denied=["create", "update", "delete", "audit"], requires_explicit_company_id=True, notes=["Leilões imobiliários em analytics ficam restritos à leitura e diagnóstico."]),
                    _rule("finance", ["discover", "read", "analyze"], denied=["create", "update", "delete", "audit"], max_risk_without_human_gate="medium", requires_explicit_company_id=True, human_gate_for_actions=["analyze"], notes=["Análises financeiras sensíveis podem exigir gate pela política vigente."]),
                    _rule("workload", ["discover", "read", "analyze"], denied=["create", "update", "delete", "audit"], requires_explicit_company_id=True, notes=["Workload é leitura analítica com company_id explícito e sem replanejamento implícito."]),
                ],
            ),
            ProfilePermissionSurfaceMatrix(
                profile="admin_tecnico",
                surface="analytics",
                title="Matriz de permissões MCP - Admin Técnico / Analytics",
                summary="Admin técnico usa analytics para diagnóstico ampliado e observabilidade, sempre em modo leitura.",
                default_scope="explicit_company_id",
                domains=[
                    _rule("analytics", ["discover", "read", "analyze"], denied=["create", "update", "delete"], requires_explicit_company_id=True, notes=["Sem mutações em analytics."]),
                    _rule("strategy", ["discover", "read", "analyze"], denied=["create", "update", "delete"], requires_explicit_company_id=True, notes=["Diagnóstico estratégico técnico continua read-only."]),
                    _rule("real_estate_auctions", ["discover", "read", "analyze"], denied=["create", "update", "delete"], requires_explicit_company_id=True, notes=["Diagnóstico técnico do módulo de leilões permanece read-only em analytics."]),
                    _rule("finance", ["discover", "read", "analyze"], denied=["create", "update", "delete"], max_risk_without_human_gate="medium", requires_explicit_company_id=True, human_gate_for_actions=["analyze"], notes=["Acesso financeiro técnico continua auditado e sem SQL livre."]),
                    _rule("workload", ["discover", "read", "analyze"], denied=["create", "update", "delete"], requires_explicit_company_id=True, notes=["Workload técnico permanece read-only mesmo na analytics."]),
                ],
            ),
            ProfilePermissionSurfaceMatrix(
                profile="admin_tecnico",
                surface="ops",
                title="Matriz de permissões MCP - Admin Técnico / Ops",
                summary="Admin técnico usa a surface ops para incidentes, intervenção e suporte operacional com escopo mínimo e auditoria obrigatória.",
                default_scope="active_company",
                domains=[
                    _rule("operations", ["discover", "read", "create", "update", "audit"], denied=["delete"], human_gate_for_actions=["update"], notes=["Operações devem manter evidência e rollback quando aplicável."]),
                    _rule("routine", ["discover", "read", "update", "audit"], denied=["delete"], human_gate_for_actions=["update"], notes=["Ajustes operacionais via ops são restritos e auditáveis."]),
                    _rule("processes", ["discover", "read", "update", "audit"], denied=["delete"], human_gate_for_actions=["update"], notes=["Intervenções em processos via ops são pontuais e auditáveis."]),
                    _rule("projects", ["discover", "read", "update", "audit"], denied=["delete"], human_gate_for_actions=["update"], notes=["Projetos em ops são intervenções pontuais, não gestão ampla."]),
                    _rule("meetings", ["discover", "read", "update", "audit"], denied=["delete"], human_gate_for_actions=["update"], notes=["Reuniões em ops ocorrem apenas em contexto de incidente ou suporte."]),
                    _rule("workload", ["discover", "read", "analyze"], denied=["create", "update", "delete"], notes=["Ops pode diagnosticar capacidade do time sem alterar alocação pela própria surface."]),
                ],
            ),
        ]
    )


APP32_PERMISSION_MATRIX_MANIFEST = build_permission_matrix_manifest()


__all__ = [
    "APP32_PERMISSION_MATRIX_MANIFEST",
    "PermissionAction",
    "PermissionDomain",
    "PermissionDomainRule",
    "PermissionMatrixEnvelope",
    "PermissionMatrixManifest",
    "OverlayPermissionSurfaceMatrix",
    "ProfilePermissionSurfaceMatrix",
    "build_permission_matrix_manifest",
]
