from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from .base import MCPSuccessEnvelope, _StrictModel


MCPProfileName = Literal["colaborador", "cliente", "administrador", "admin_tecnico"]
MCPOverlayName = Literal[
    "coordenador_cliente",
    "comercial_cliente",
    "operacional_cliente",
    "admfin_cliente",
    "estrategico_cliente",
    "pessoas_capacidade_cliente",
    "coordenador_versus",
    "strategist_versus",
    "pmo_controller_versus",
    "business_architect_versus",
    "operations_versus",
    "followup_collector_versus",
    "performance_analyst_versus",
    "finance_versus",
    "auditor_versus",
    "coordenador_engenharia",
    "arquiteto_engenharia",
    "frontend_engenharia",
    "backend_api_engenharia",
    "backend_service_engenharia",
    "ai_engineer_engenharia",
    "dba_engenharia",
    "qa_automation_engenharia",
]
MCPAllowedSurface = Literal["user", "admin", "analytics", "ops"]
MCPMutationRisk = Literal["low", "medium", "high", "critical"]


class MCPProfileContract(_StrictModel):
    profile: MCPProfileName
    allowed_surfaces: list[MCPAllowedSurface] = Field(default_factory=list, min_length=1)
    default_surface: MCPAllowedSurface
    allowed_domains: list[str] = Field(default_factory=list, min_length=1)
    forbidden_domains: list[str] = Field(default_factory=list)
    max_risk_without_human_gate: MCPMutationRisk = "medium"
    requires_explicit_company_for_admin_surfaces: bool = True
    can_execute_mutations: bool = False
    can_execute_financial_mutations: bool = False
    can_access_admin_domains: bool = False
    can_access_analytics: bool = False
    can_access_ops: bool = False
    tenant_scope_required: bool = True
    audit_required: bool = True

    @model_validator(mode="after")
    def _validate_profile_contract(self):
        if self.default_surface not in self.allowed_surfaces:
            raise ValueError("default_surface deve pertencer a allowed_surfaces.")
        if not self.tenant_scope_required or not self.audit_required:
            raise ValueError("Contratos de perfil MCP exigem tenant_scope_required=True e audit_required=True.")
        if self.profile in {"colaborador", "cliente"} and any(
            surface in {"admin", "analytics", "ops"} for surface in self.allowed_surfaces
        ):
            raise ValueError("Perfis não administrativos não podem acessar surfaces privilegiadas.")
        if self.can_execute_financial_mutations and self.profile not in {"administrador", "admin_tecnico"}:
            raise ValueError("Mutações financeiras ficam restritas a perfis administrativos.")
        if self.can_access_ops and self.profile != "admin_tecnico":
            raise ValueError("Surface ops fica restrita ao perfil admin_tecnico.")
        return self


class MCPRoleOverlayContract(_StrictModel):
    overlay: MCPOverlayName
    runtime_profile: str = Field(min_length=3, max_length=80)
    title: str = Field(min_length=8, max_length=160)
    summary: str = Field(min_length=16, max_length=360)
    compatible_profiles: list[MCPProfileName] = Field(default_factory=list, min_length=1)
    surface: MCPAllowedSurface = "user"
    harness_key: str = Field(min_length=8, max_length=120)
    harness_label: str = Field(min_length=8, max_length=180)
    allowed_domains: list[str] = Field(default_factory=list, min_length=1)
    allowed_actions: list[str] = Field(default_factory=list, min_length=1)
    blocked_domains: list[str] = Field(default_factory=list)
    escalation_notes: list[str] = Field(default_factory=list, min_length=1)

    @model_validator(mode="after")
    def _validate_overlay(self):
        if self.runtime_profile == "squad_cliente":
            if self.surface != "user":
                raise ValueError("Overlays canônicos do Squad Cliente operam na surface user.")
            if "finance" in self.allowed_domains:
                raise ValueError("Overlay do Squad Cliente não pode liberar finanças sensíveis na surface user.")
            if "finance" not in self.blocked_domains:
                raise ValueError("Overlay do Squad Cliente deve bloquear finance explicitamente.")
        elif self.runtime_profile == "squad_versus":
            if self.surface not in {"admin", "analytics"}:
                raise ValueError("Overlays do Squad Versus devem operar em admin ou analytics.")
            if not set(self.compatible_profiles).issubset({"administrador"}):
                raise ValueError("Overlays do Squad Versus devem se apoiar no perfil base administrador.")
            if self.overlay == "auditor_versus" and any(
                action in self.allowed_actions for action in {"create", "update", "delete"}
            ):
                raise ValueError("Overlay auditor_versus deve permanecer read-only.")
        elif self.runtime_profile == "engineering":
            if self.surface not in {"ops", "admin", "analytics"}:
                raise ValueError("Overlays de Engenharia devem operar em ops, admin ou analytics.")
            if not set(self.compatible_profiles).issubset({"admin_tecnico"}):
                raise ValueError("Overlays de Engenharia devem se apoiar no perfil base admin_tecnico.")
        else:
            raise ValueError("runtime_profile de overlay MCP não suportado.")
        return self


class MCPProfileContractsManifest(_StrictModel):
    version: str = Field(default="app32.mcp.profiles.v1", min_length=1, max_length=80)
    profiles: list[MCPProfileContract] = Field(default_factory=list, min_length=1)
    role_overlays: list[MCPRoleOverlayContract] = Field(default_factory=list)

    def get_profile(self, profile: MCPProfileName | str) -> MCPProfileContract | None:
        normalized = str(profile).strip().lower()
        alias = "admin_tecnico" if normalized == "administrador_tecnico" else normalized
        for contract in self.profiles:
            if contract.profile == alias:
                return contract
        return None

    def get_overlay(self, overlay: MCPOverlayName | str) -> MCPRoleOverlayContract | None:
        normalized = str(overlay).strip().lower()
        for item in self.role_overlays:
            if item.overlay == normalized or item.harness_key == normalized:
                return item
        return None

    def get_overlays_for_profile(self, profile: MCPProfileName | str) -> list[MCPRoleOverlayContract]:
        normalized = str(profile).strip().lower()
        alias = "admin_tecnico" if normalized == "administrador_tecnico" else normalized
        return [item for item in self.role_overlays if alias in item.compatible_profiles]


MCPProfileContractsEnvelope = MCPSuccessEnvelope[MCPProfileContractsManifest | MCPProfileContract]


def build_app32_profile_contracts_manifest() -> MCPProfileContractsManifest:
    return MCPProfileContractsManifest(
        role_overlays=[
            MCPRoleOverlayContract(
                overlay="coordenador_versus",
                runtime_profile="squad_versus",
                title="Overlay Canônico — Coordenador do Squad Versus",
                summary="Entrada consultiva do Squad Versus, responsável por discovery, enquadramento e roteamento metodológico da intervenção.",
                compatible_profiles=["administrador"],
                surface="admin",
                harness_key="harness_coordenador_versus_v1",
                harness_label="Harness Coordenador do Squad Versus",
                allowed_domains=["routine", "projects", "processes", "meetings", "strategy", "governance", "finance"],
                allowed_actions=["discover", "read", "analyze", "update"],
                blocked_domains=["operations", "identity_admin"],
                escalation_notes=[
                    "Escalar intervenções técnicas de plataforma para o Squad de Engenharia.",
                    "Começar por discovery antes de qualquer mutação consultiva.",
                ],
            ),
            MCPRoleOverlayContract(
                overlay="strategist_versus",
                runtime_profile="squad_versus",
                title="Overlay Canônico — Strategist Versus",
                summary="Foco em direção estratégica, crescimento, planos, indicadores e leitura sistêmica do negócio do cliente.",
                compatible_profiles=["administrador"],
                surface="admin",
                harness_key="harness_strategist_versus_v1",
                harness_label="Harness Strategist Versus",
                allowed_domains=["strategy", "projects", "meetings", "governance"],
                allowed_actions=["discover", "read", "analyze", "update"],
                blocked_domains=["operations", "identity_admin"],
                escalation_notes=[
                    "Usar analytics quando a leitura exigir envelopes executivos.",
                    "Escalar finanças profundas para finance_versus.",
                ],
            ),
            MCPRoleOverlayContract(
                overlay="pmo_controller_versus",
                runtime_profile="squad_versus",
                title="Overlay Canônico — PMO Controller Versus",
                summary="Orquestra cadência, follow-up, governança de execução e cobrança estruturada de andamento.",
                compatible_profiles=["administrador"],
                surface="admin",
                harness_key="harness_pmo_controller_versus_v1",
                harness_label="Harness PMO Controller Versus",
                allowed_domains=["routine", "projects", "processes", "meetings", "strategy", "governance"],
                allowed_actions=["discover", "read", "analyze", "update"],
                blocked_domains=["operations", "identity_admin"],
                escalation_notes=[
                    "Manter trilha consultiva e evidência de cobrança/fechamento.",
                    "Escalar incidentes operacionais para operations_versus ou Engenharia.",
                ],
            ),
            MCPRoleOverlayContract(
                overlay="business_architect_versus",
                runtime_profile="squad_versus",
                title="Overlay Canônico — Business Architect Versus",
                summary="Responsável por estruturação de processos, desenho operacional e coerência entre método, processo e capability.",
                compatible_profiles=["administrador"],
                surface="admin",
                harness_key="harness_business_architect_versus_v1",
                harness_label="Harness Business Architect Versus",
                allowed_domains=["routine", "projects", "processes", "meetings", "strategy", "governance"],
                allowed_actions=["discover", "read", "analyze", "update"],
                blocked_domains=["operations", "identity_admin"],
                escalation_notes=[
                    "Escalar mudanças técnicas de plataforma para o Squad de Engenharia.",
                    "Escalar números/controladoria para finance_versus.",
                ],
            ),
            MCPRoleOverlayContract(
                overlay="operations_versus",
                runtime_profile="squad_versus",
                title="Overlay Canônico — Operations Versus",
                summary="Leitura crítica e orientação sobre disciplina operacional, processos, rotina e execução assistida do cliente.",
                compatible_profiles=["administrador"],
                surface="admin",
                harness_key="harness_operations_versus_v1",
                harness_label="Harness Operations Versus",
                allowed_domains=["routine", "projects", "processes", "meetings", "strategy"],
                allowed_actions=["discover", "read", "analyze", "update"],
                blocked_domains=["operations", "identity_admin"],
                escalation_notes=[
                    "Não usar ops como atalho; escalar plataforma para Engenharia.",
                    "Escalar governança estrutural para business_architect_versus ou coordenador.",
                ],
            ),
            MCPRoleOverlayContract(
                overlay="followup_collector_versus",
                runtime_profile="squad_versus",
                title="Overlay Canônico — Follow-up Collector Versus",
                summary="Especialista em cobrança estruturada, fechamento de pendências e manutenção da cadência entre Versus e cliente.",
                compatible_profiles=["administrador"],
                surface="admin",
                harness_key="harness_followup_collector_versus_v1",
                harness_label="Harness Follow-up Collector Versus",
                allowed_domains=["routine", "projects", "meetings", "governance"],
                allowed_actions=["discover", "read", "analyze", "update"],
                blocked_domains=["operations", "identity_admin", "finance"],
                escalation_notes=[
                    "Escalar temas financeiros para finance_versus.",
                    "Escalar temas estratégicos profundos para strategist_versus ou PMO.",
                ],
            ),
            MCPRoleOverlayContract(
                overlay="performance_analyst_versus",
                runtime_profile="squad_versus",
                title="Overlay Canônico — Performance Analyst Versus",
                summary="Especialista de leitura analítica, indicadores e sinais de performance com foco executivo e sem mutação.",
                compatible_profiles=["administrador"],
                surface="analytics",
                harness_key="harness_performance_analyst_versus_v1",
                harness_label="Harness Performance Analyst Versus",
                allowed_domains=["analytics", "strategy", "workload"],
                allowed_actions=["discover", "read", "analyze"],
                blocked_domains=["finance", "operations", "identity_admin"],
                escalation_notes=[
                    "Escalar mutação de plano para strategist_versus ou coordenador.",
                    "Escalar números financeiros para finance_versus.",
                ],
            ),
            MCPRoleOverlayContract(
                overlay="finance_versus",
                runtime_profile="squad_versus",
                title="Overlay Canônico — Finance Versus",
                summary="Controladoria e leitura econômico-financeira controlada, com governança e eventual mutação apenas quando o rito exigir.",
                compatible_profiles=["administrador"],
                surface="admin",
                harness_key="harness_finance_versus_v1",
                harness_label="Harness Finance Versus",
                allowed_domains=["finance", "strategy", "governance"],
                allowed_actions=["discover", "read", "analyze", "update"],
                blocked_domains=["operations", "identity_admin"],
                escalation_notes=[
                    "Toda mutação financeira relevante deve manter gate humano e trilha auditável.",
                    "Escalar auditoria independente para auditor_versus.",
                ],
            ),
            MCPRoleOverlayContract(
                overlay="auditor_versus",
                runtime_profile="squad_versus",
                title="Overlay Canônico — Auditor Versus",
                summary="Auditoria e conformidade em modo read-only, com leitura crítica de governança, finanças e execução.",
                compatible_profiles=["administrador"],
                surface="analytics",
                harness_key="harness_auditor_versus_v1",
                harness_label="Harness Auditor Versus",
                allowed_domains=["analytics", "finance", "strategy", "governance", "workload"],
                allowed_actions=["discover", "read", "analyze", "audit"],
                blocked_domains=["operations", "identity_admin"],
                escalation_notes=[
                    "Não mutar dados; apenas recomendar achados e escalonamentos.",
                    "Encaminhar mudança corretiva ao coordenador, strategist ou Engenharia conforme o caso.",
                ],
            ),
            MCPRoleOverlayContract(
                overlay="coordenador_engenharia",
                runtime_profile="engineering",
                title="Overlay Canônico — Coordenador do Squad de Engenharia",
                summary="Entrada técnica do Squad de Engenharia para triagem, priorização, diagnóstico e roteamento disciplinado.",
                compatible_profiles=["admin_tecnico"],
                surface="ops",
                harness_key="harness_coordenador_engenharia_v1",
                harness_label="Harness Coordenador do Squad de Engenharia",
                allowed_domains=["operations", "routine", "processes", "projects", "meetings", "workload", "governance"],
                allowed_actions=["discover", "read", "analyze", "audit", "update"],
                blocked_domains=["finance"],
                escalation_notes=[
                    "Roteia para especialista técnico adequado conforme o tipo de problema.",
                    "Não operar o negócio como se fosse o cliente ou a consultoria.",
                ],
            ),
            MCPRoleOverlayContract(
                overlay="arquiteto_engenharia",
                runtime_profile="engineering",
                title="Overlay Canônico — Arquiteto de Engenharia",
                summary="Especialista de boundary, segurança, arquitetura e coerência estrutural do APP32 e do ecossistema MCP.",
                compatible_profiles=["admin_tecnico"],
                surface="admin",
                harness_key="harness_arquiteto_engenharia_v1",
                harness_label="Harness Arquiteto de Engenharia",
                allowed_domains=["governance", "strategy", "identity_admin", "analytics"],
                allowed_actions=["discover", "read", "analyze", "audit", "update"],
                blocked_domains=["finance", "operations"],
                escalation_notes=[
                    "Escalar incidentes runtime para coordenador/ops.",
                    "Manter foco estrutural e não cair em operação de negócio.",
                ],
            ),
            MCPRoleOverlayContract(
                overlay="frontend_engenharia",
                runtime_profile="engineering",
                title="Overlay Canônico — Frontend de Engenharia",
                summary="Especialista em UX, templates e experiência operacional, atuando em diagnóstico e ajustes técnicos de interface.",
                compatible_profiles=["admin_tecnico"],
                surface="ops",
                harness_key="harness_frontend_engenharia_v1",
                harness_label="Harness Frontend de Engenharia",
                allowed_domains=["operations", "routine", "projects", "meetings"],
                allowed_actions=["discover", "read", "analyze", "audit", "update"],
                blocked_domains=["finance", "identity_admin"],
                escalation_notes=[
                    "Escalar contratos/schemas para backend_api.",
                    "Escalar boundary/segurança para arquiteto.",
                ],
            ),
            MCPRoleOverlayContract(
                overlay="backend_api_engenharia",
                runtime_profile="engineering",
                title="Overlay Canônico — Backend API de Engenharia",
                summary="Especialista em contratos REST/MCP, validação de entrada, surfaces e coerência de publicação de capabilities.",
                compatible_profiles=["admin_tecnico"],
                surface="admin",
                harness_key="harness_backend_api_engenharia_v1",
                harness_label="Harness Backend API de Engenharia",
                allowed_domains=["governance", "identity_admin", "analytics", "strategy"],
                allowed_actions=["discover", "read", "analyze", "audit", "update"],
                blocked_domains=["finance", "operations"],
                escalation_notes=[
                    "Escalar regra de negócio para backend_service.",
                    "Escalar auth/OAuth e boundary crítico para arquiteto.",
                ],
            ),
            MCPRoleOverlayContract(
                overlay="backend_service_engenharia",
                runtime_profile="engineering",
                title="Overlay Canônico — Backend Service de Engenharia",
                summary="Especialista em regra de negócio determinística e services reutilizáveis, com foco em execução e consistência operacional.",
                compatible_profiles=["admin_tecnico"],
                surface="ops",
                harness_key="harness_backend_service_engenharia_v1",
                harness_label="Harness Backend Service de Engenharia",
                allowed_domains=["operations", "routine", "processes", "projects", "meetings", "governance"],
                allowed_actions=["discover", "read", "analyze", "audit", "update"],
                blocked_domains=["finance", "identity_admin"],
                escalation_notes=[
                    "Escalar contratos e surfaces para backend_api.",
                    "Escalar performance SQL para DBA.",
                ],
            ),
            MCPRoleOverlayContract(
                overlay="ai_engineer_engenharia",
                runtime_profile="engineering",
                title="Overlay Canônico — AI Engineer de Engenharia",
                summary="Especialista em agentes, LangGraph, RAG, MCP e orquestração de runtime inteligente do APP32.",
                compatible_profiles=["admin_tecnico"],
                surface="admin",
                harness_key="harness_ai_engineer_engenharia_v1",
                harness_label="Harness AI Engineer de Engenharia",
                allowed_domains=["governance", "analytics", "strategy", "identity_admin"],
                allowed_actions=["discover", "read", "analyze", "audit", "update"],
                blocked_domains=["finance", "operations"],
                escalation_notes=[
                    "Escalar boundary/segurança para arquiteto.",
                    "Escalar runtime incidente para coordenador/ops.",
                ],
            ),
            MCPRoleOverlayContract(
                overlay="dba_engenharia",
                runtime_profile="engineering",
                title="Overlay Canônico — DBA de Engenharia",
                summary="Especialista em PostgreSQL, dados, migração, índices e diagnósticos de performance e integridade.",
                compatible_profiles=["admin_tecnico"],
                surface="analytics",
                harness_key="harness_dba_engenharia_v1",
                harness_label="Harness DBA de Engenharia",
                allowed_domains=["analytics", "workload", "governance", "strategy"],
                allowed_actions=["discover", "read", "analyze", "audit"],
                blocked_domains=["finance", "operations", "identity_admin"],
                escalation_notes=[
                    "Não usar SQL livre fora dos contratos; operar por diagnóstico whitelisted.",
                    "Escalar mutações estruturais para coordenador/arquitetura.",
                ],
            ),
            MCPRoleOverlayContract(
                overlay="qa_automation_engenharia",
                runtime_profile="engineering",
                title="Overlay Canônico — QA Automation de Engenharia",
                summary="Especialista em smoke, regressão, evidência e validação disciplinada do comportamento do APP32 e MCP.",
                compatible_profiles=["admin_tecnico"],
                surface="ops",
                harness_key="harness_qa_automation_engenharia_v1",
                harness_label="Harness QA Automation de Engenharia",
                allowed_domains=["operations", "routine", "processes", "projects", "meetings", "workload", "governance"],
                allowed_actions=["discover", "read", "analyze", "audit", "update"],
                blocked_domains=["finance", "identity_admin"],
                escalation_notes=[
                    "Usar analytics/admin apenas quando o caso exigir investigação complementar.",
                    "Escalar correção estrutural para o especialista técnico apropriado.",
                ],
            ),
            MCPRoleOverlayContract(
                overlay="coordenador_cliente",
                runtime_profile="squad_cliente",
                title="Overlay Canônico — Coordenador do Squad Cliente",
                summary="Papel de entrada e roteamento do Squad Cliente, com visão ampla de operação assistida na surface user.",
                compatible_profiles=["cliente", "colaborador", "administrador"],
                surface="user",
                harness_key="harness_coordenador_cliente_v1",
                harness_label="Harness Coordenador do Squad Cliente",
                allowed_domains=["routine", "projects", "processes", "meetings", "strategy", "identity_self_service"],
                allowed_actions=["discover", "read", "create", "update", "analyze"],
                blocked_domains=["finance", "governance", "analytics", "operations", "identity_admin", "workload"],
                escalation_notes=[
                    "Escalar finanças sensíveis para admin/analytics.",
                    "Usar o coordenador como front door antes de acionar harness especializado.",
                ],
            ),
            MCPRoleOverlayContract(
                overlay="comercial_cliente",
                runtime_profile="squad_cliente",
                title="Overlay Canônico — Comercial do Squad Cliente",
                summary="Copiloto de contexto comercial com foco em jornada, relacionamento, tarefas, projetos e sinais estratégicos de crescimento.",
                compatible_profiles=["cliente", "colaborador", "administrador"],
                surface="user",
                harness_key="harness_comercial_cliente_v1",
                harness_label="Harness Comercial do Squad Cliente",
                allowed_domains=["routine", "projects", "meetings", "strategy", "identity_self_service"],
                allowed_actions=["discover", "read", "create", "update", "analyze"],
                blocked_domains=["finance", "governance", "analytics", "operations", "identity_admin", "workload"],
                escalation_notes=[
                    "Não tratar financeiro sensível pela surface user.",
                    "Escalar modelagens estratégicas profundas para Versus ou analytics.",
                ],
            ),
            MCPRoleOverlayContract(
                overlay="operacional_cliente",
                runtime_profile="squad_cliente",
                title="Overlay Canônico — Operacional do Squad Cliente",
                summary="Copiloto voltado à execução operacional, processos, rotina, projetos e coordenação de reuniões do dia a dia.",
                compatible_profiles=["cliente", "colaborador", "administrador"],
                surface="user",
                harness_key="harness_operacional_cliente_v1",
                harness_label="Harness Operacional do Squad Cliente",
                allowed_domains=["routine", "projects", "processes", "meetings", "identity_self_service"],
                allowed_actions=["discover", "read", "create", "update"],
                blocked_domains=["finance", "governance", "analytics", "operations", "identity_admin", "workload"],
                escalation_notes=[
                    "Escalar análise executiva aprofundada para coordenador/estratégico.",
                    "Escalar suporte técnico ou incidente para ops.",
                ],
            ),
            MCPRoleOverlayContract(
                overlay="admfin_cliente",
                runtime_profile="squad_cliente",
                title="Overlay Canônico — Adm/Financeiro do Squad Cliente",
                summary="Copiloto administrativo/financeiro em menor privilégio, capaz de organizar contexto e leitura operacional sem mutação financeira sensível.",
                compatible_profiles=["cliente", "colaborador", "administrador"],
                surface="user",
                harness_key="harness_admfin_cliente_v1",
                harness_label="Harness Adm/Financeiro do Squad Cliente",
                allowed_domains=["routine", "projects", "meetings", "strategy", "identity_self_service"],
                allowed_actions=["discover", "read", "analyze"],
                blocked_domains=["finance", "governance", "analytics", "operations", "identity_admin", "workload"],
                escalation_notes=[
                    "Toda mutação financeira sensível deve migrar para surface admin com gate humano.",
                    "Leituras financeiras executivas devem ocorrer por analytics/admin quando publicadas.",
                ],
            ),
            MCPRoleOverlayContract(
                overlay="estrategico_cliente",
                runtime_profile="squad_cliente",
                title="Overlay Canônico — Estratégico do Squad Cliente",
                summary="Copiloto do cliente para priorização, planos, indicadores e síntese estratégica em modo assistido.",
                compatible_profiles=["cliente", "colaborador", "administrador"],
                surface="user",
                harness_key="harness_estrategico_cliente_v1",
                harness_label="Harness Estratégico do Squad Cliente",
                allowed_domains=["strategy", "projects", "meetings", "identity_self_service"],
                allowed_actions=["discover", "read", "analyze"],
                blocked_domains=["finance", "governance", "analytics", "operations", "identity_admin", "workload"],
                escalation_notes=[
                    "Usar analytics quando a análise exigir read model executivo.",
                    "Escalar mudança estrutural de plano para admin com confirmação.",
                ],
            ),
            MCPRoleOverlayContract(
                overlay="pessoas_capacidade_cliente",
                runtime_profile="squad_cliente",
                title="Overlay Canônico — Pessoas/Capacidade do Squad Cliente",
                summary="Copiloto focado em pessoas, capacidade e coordenação operacional sem acesso analítico privilegiado.",
                compatible_profiles=["cliente", "colaborador", "administrador"],
                surface="user",
                harness_key="harness_pessoas_capacidade_cliente_v1",
                harness_label="Harness Pessoas/Capacidade do Squad Cliente",
                allowed_domains=["routine", "projects", "meetings", "identity_self_service"],
                allowed_actions=["discover", "read", "create", "update"],
                blocked_domains=["finance", "governance", "analytics", "operations", "identity_admin", "workload", "strategy"],
                escalation_notes=[
                    "Capacidade analítica consolidada deve migrar para analytics por perfil administrativo.",
                    "Não usar este overlay para gestão de acesso administrativo.",
                ],
            ),
        ],
        profiles=[
            MCPProfileContract(
                profile="colaborador",
                allowed_surfaces=["user"],
                default_surface="user",
                allowed_domains=["routine", "projects", "processes", "meetings", "strategy", "identity_self_service"],
                forbidden_domains=["finance", "governance", "admin", "analytics", "operations", "workload", "identity_admin"],
                max_risk_without_human_gate="medium",
                can_execute_mutations=True,
            ),
            MCPProfileContract(
                profile="cliente",
                allowed_surfaces=["user"],
                default_surface="user",
                allowed_domains=["routine", "projects", "processes", "meetings", "strategy", "identity_self_service"],
                forbidden_domains=["finance", "governance", "admin", "analytics", "operations", "workload", "identity_admin"],
                max_risk_without_human_gate="low",
                can_execute_mutations=False,
            ),
            MCPProfileContract(
                profile="administrador",
                allowed_surfaces=["user", "admin", "analytics"],
                default_surface="admin",
                allowed_domains=[
                    "routine",
                    "projects",
                    "processes",
                    "meetings",
                    "finance",
                    "strategy",
                    "governance",
                    "analytics",
                    "workload",
                    "identity_self_service",
                    "identity_admin",
                ],
                forbidden_domains=["operations"],
                max_risk_without_human_gate="medium",
                can_execute_mutations=True,
                can_execute_financial_mutations=True,
                can_access_admin_domains=True,
                can_access_analytics=True,
            ),
            MCPProfileContract(
                profile="admin_tecnico",
                allowed_surfaces=["admin", "analytics", "ops"],
                default_surface="ops",
                allowed_domains=[
                    "routine",
                    "projects",
                    "processes",
                    "meetings",
                    "finance",
                    "strategy",
                    "governance",
                    "analytics",
                    "workload",
                    "operations",
                    "identity_self_service",
                    "identity_admin",
                ],
                forbidden_domains=[],
                max_risk_without_human_gate="medium",
                can_execute_mutations=True,
                can_execute_financial_mutations=True,
                can_access_admin_domains=True,
                can_access_analytics=True,
                can_access_ops=True,
            ),
        ]
    )


APP32_PROFILE_CONTRACTS_MANIFEST = build_app32_profile_contracts_manifest()


__all__ = [
    "APP32_PROFILE_CONTRACTS_MANIFEST",
    "MCPAllowedSurface",
    "MCPMutationRisk",
    "MCPOverlayName",
    "MCPProfileContract",
    "MCPProfileContractsEnvelope",
    "MCPProfileContractsManifest",
    "MCPProfileName",
    "MCPRoleOverlayContract",
    "build_app32_profile_contracts_manifest",
]
