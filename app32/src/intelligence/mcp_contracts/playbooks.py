from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from .base import MCPSuccessEnvelope, _StrictModel
from .profiles import MCPOverlayName


PlaybookSurface = Literal["user", "admin", "analytics", "ops"]
PlaybookRole = Literal["colaborador", "cliente", "administrador", "admin_tecnico"]


class SurfaceInteractionRule(_StrictModel):
    rule: str = Field(min_length=8, max_length=320)
    rationale: str = Field(min_length=8, max_length=320)


class SurfaceExampleFlow(_StrictModel):
    title: str = Field(min_length=4, max_length=140)
    steps: list[str] = Field(default_factory=list, min_length=1)


class SurfaceRoleOverlayGuide(_StrictModel):
    overlay: MCPOverlayName
    title: str = Field(min_length=8, max_length=160)
    harness_key: str = Field(min_length=8, max_length=120)
    primary_domains: list[str] = Field(default_factory=list, min_length=1)
    recommended_actions: list[str] = Field(default_factory=list, min_length=1)
    escalation_rules: list[str] = Field(default_factory=list, min_length=1)


class SurfacePlaybook(_StrictModel):
    """Playbook canônico de interação de agentes por surface MCP."""

    surface: PlaybookSurface
    title: str = Field(min_length=4, max_length=140)
    objective: str = Field(min_length=16, max_length=500)
    actor_roles: list[PlaybookRole] = Field(default_factory=list, min_length=1)
    allowed_domains: list[str] = Field(default_factory=list, min_length=1)
    default_scope: Literal["active_company", "explicit_company_id", "none"] = "active_company"
    discovery_tools: list[str] = Field(default_factory=list, min_length=1)
    startup_checklist: list[str] = Field(default_factory=list, min_length=2)
    interaction_rules: list[SurfaceInteractionRule] = Field(default_factory=list, min_length=2)
    forbidden_actions: list[str] = Field(default_factory=list, min_length=1)
    example_flows: list[SurfaceExampleFlow] = Field(default_factory=list, min_length=1)
    role_overlays: list[SurfaceRoleOverlayGuide] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_surface_rules(self):
        if self.surface == "analytics" and self.default_scope == "none":
            raise ValueError("Surface analytics deve operar com escopo explícito ou empresa ativa.")
        for overlay in self.role_overlays:
            if self.surface == "user" and not overlay.overlay.endswith("_cliente"):
                raise ValueError("Surface user deve expor apenas overlays do Squad Cliente.")
            if self.surface == "admin" and not (overlay.overlay.endswith("_versus") or overlay.overlay.endswith("_engenharia")):
                raise ValueError("Surface admin deve expor overlays de Squad Versus ou Engenharia.")
            if self.surface == "analytics" and not (overlay.overlay.endswith("_versus") or overlay.overlay.endswith("_engenharia")):
                raise ValueError("Surface analytics deve expor overlays de Squad Versus ou Engenharia.")
            if self.surface == "ops" and not overlay.overlay.endswith("_engenharia"):
                raise ValueError("Surface ops deve expor apenas overlays de Engenharia.")
        if self.surface == "analytics":
            forbidden = "nunca mutar dados"
            if not any(forbidden in action.lower() for action in self.forbidden_actions):
                raise ValueError("Playbook analytics deve proibir mutação de dados explicitamente.")
        return self


class SurfacePlaybooksManifest(_StrictModel):
    version: str = Field(default="app32.mcp.playbooks.v1", min_length=1, max_length=80)
    playbooks: list[SurfacePlaybook] = Field(default_factory=list, min_length=1)

    def get_surface(self, surface: PlaybookSurface) -> SurfacePlaybook | None:
        normalized = str(surface).strip().lower()
        for playbook in self.playbooks:
            if playbook.surface == normalized:
                return playbook
        return None


SurfacePlaybooksEnvelope = MCPSuccessEnvelope[SurfacePlaybooksManifest | SurfacePlaybook]


def build_surface_playbooks_manifest() -> SurfacePlaybooksManifest:
    return SurfacePlaybooksManifest(
        playbooks=[
            SurfacePlaybook(
                surface="user",
                title="Playbook MCP User",
                objective="Executar fluxos operacionais do usuário final com escopo tenant-safe, menor privilégio e exposição permission-aware das tools liberadas na senha do APP32.",
                actor_roles=["colaborador", "cliente", "administrador"],
                allowed_domains=[
                    "routine",
                    "projects",
                    "processes",
                    "meetings",
                    "strategy",
                    "consultive",
                    "knowledge",
                    "real_estate_auctions",
                    "finance",
                    "identity_self_service",
                ],
                default_scope="active_company",
                discovery_tools=["list_user_app32_capabilities", "describe_app32_crud_contracts_tool"],
                startup_checklist=[
                    "Confirmar company_id ativo antes de qualquer leitura ou mutação.",
                    "Consultar as capabilities da surface user e o contrato CRUD do domínio alvo.",
                    "Quando o domínio for finance, depender apenas das tools efetivamente liberadas pelas permissões web do usuário na empresa ativa.",
                    "Se houver ambiguidade de escopo, pedir confirmação ao usuário antes de agir.",
                ],
                interaction_rules=[
                    SurfaceInteractionRule(
                        rule="Usar primeiro as tools de descoberta e contrato antes da tool operacional.",
                        rationale="Reduz erro de surface, domínio e permissão.",
                    ),
                    SurfaceInteractionRule(
                        rule="Priorizar ações dentro da empresa ativa e do contexto do próprio usuário.",
                        rationale="Evita vazamento cross-tenant e ações fora do papel do ator.",
                    ),
                ],
                forbidden_actions=[
                    "Não acessar tools exclusivas de admin, analytics ou ops.",
                    "Não executar ação financeira fora das permissões web equivalentes do usuário, do company_id ativo e do tenant autorizado.",
                ],
                example_flows=[
                    SurfaceExampleFlow(
                        title="Criar tarefa em projeto",
                        steps=[
                            "Ler capabilities da surface user.",
                            "Consultar contrato CRUD de projects.",
                            "Executar create_project_task no tenant ativo.",
                        ],
                    )
                ],
                role_overlays=[
                    SurfaceRoleOverlayGuide(
                        overlay="coordenador_cliente",
                        title="Coordenador do Squad Cliente",
                        harness_key="harness_coordenador_cliente_v1",
                        primary_domains=["routine", "projects", "processes", "meetings", "strategy", "knowledge"],
                        recommended_actions=["discover", "read", "create", "update", "analyze"],
                        escalation_rules=["Acionar harness especializado quando a intenção sair do roteamento inicial.", "Escalar finanças sensíveis para admin/analytics."],
                    ),
                    SurfaceRoleOverlayGuide(
                        overlay="comercial_cliente",
                        title="Comercial do Squad Cliente",
                        harness_key="harness_comercial_cliente_v1",
                        primary_domains=["routine", "projects", "meetings", "strategy"],
                        recommended_actions=["discover", "read", "create", "update", "analyze"],
                        escalation_rules=["Escalar modelagem financeira para Adm/Financeiro ou admin.", "Escalar operação técnica para o overlay operacional."],
                    ),
                    SurfaceRoleOverlayGuide(
                        overlay="operacional_cliente",
                        title="Operacional do Squad Cliente",
                        harness_key="harness_operacional_cliente_v1",
                        primary_domains=["routine", "projects", "processes", "meetings"],
                        recommended_actions=["discover", "read", "create", "update"],
                        escalation_rules=["Escalar incidente técnico para ops.", "Escalar consolidação estratégica para coordenador/estratégico."],
                    ),
                    SurfaceRoleOverlayGuide(
                        overlay="admfin_cliente",
                        title="Adm/Financeiro do Squad Cliente",
                        harness_key="harness_admfin_cliente_v1",
                        primary_domains=["routine", "projects", "meetings", "strategy", "finance"],
                        recommended_actions=["discover", "read", "create", "update", "analyze"],
                        escalation_rules=["Operar finanças somente quando a senha do usuário liberar a tool equivalente no APP32.", "Escalar governança multiempresa e leitura executiva ampliada para admin/analytics quando o rito exigir."],
                    ),
                    SurfaceRoleOverlayGuide(
                        overlay="estrategico_cliente",
                        title="Estratégico do Squad Cliente",
                        harness_key="harness_estrategico_cliente_v1",
                        primary_domains=["strategy", "consultive", "projects", "meetings"],
                        recommended_actions=["discover", "read", "analyze"],
                        escalation_rules=["Escalar mutação estrutural de plano para admin.", "Usar analytics quando o caso exigir read model executivo."],
                    ),
                    SurfaceRoleOverlayGuide(
                        overlay="pessoas_capacidade_cliente",
                        title="Pessoas/Capacidade do Squad Cliente",
                        harness_key="harness_pessoas_capacidade_cliente_v1",
                        primary_domains=["routine", "projects", "meetings"],
                        recommended_actions=["discover", "read", "create", "update"],
                        escalation_rules=["Não abrir workload analítico privilegiado na surface user.", "Escalar gestão de acesso para admin."],
                    ),
                ],
            ),
            SurfacePlaybook(
                surface="admin",
                title="Playbook MCP Admin",
                objective="Executar operações administrativas explícitas com governança, auditoria e gates humanos.",
                actor_roles=["administrador", "admin_tecnico"],
                allowed_domains=[
                    "routine",
                    "projects",
                    "processes",
                    "meetings",
                    "finance",
                    "strategy",
                    "consultive",
                    "real_estate_auctions",
                    "governance",
                    "identity_self_service",
                    "identity_admin",
                ],
                default_scope="explicit_company_id",
                discovery_tools=["list_admin_app32_capabilities", "describe_app32_crud_contracts_tool"],
                startup_checklist=[
                    "Validar surface admin e domínio pretendido antes de agir.",
                    "Confirmar company_id explícito para operações sensíveis ou multiempresa.",
                    "Verificar se a ação exige gate humano ou permissão administrativa reforçada.",
                ],
                interaction_rules=[
                    SurfaceInteractionRule(
                        rule="Usar admin apenas para ações realmente administrativas ou restritas.",
                        rationale="Evita concentrar tudo em uma surface com privilégio elevado.",
                    ),
                    SurfaceInteractionRule(
                        rule="Para high/critical risk, registrar intenção e exigir confirmação humana.",
                        rationale="Mantém trilha auditável e controle de mudança.",
                    ),
                ],
                forbidden_actions=[
                    "Não assumir acesso global sem company_id quando o contrato exigir escopo explícito.",
                    "Não usar admin para analytics read-only se a surface analytics atender ao caso.",
                ],
                example_flows=[
                    SurfaceExampleFlow(
                        title="Atualizar configuração administrativa",
                        steps=[
                            "Consultar capabilities admin.",
                            "Validar contrato do domínio e risco da operação.",
                            "Solicitar confirmação humana quando exigido e só então executar.",
                        ],
                    )
                ],
                role_overlays=[
                    SurfaceRoleOverlayGuide(
                        overlay="coordenador_versus",
                        title="Coordenador do Squad Versus",
                        harness_key="harness_coordenador_versus_v1",
                        primary_domains=["routine", "projects", "processes", "meetings", "strategy", "governance", "finance"],
                        recommended_actions=["discover", "read", "analyze", "update"],
                        escalation_rules=["Começar por discovery antes de qualquer mutação.", "Escalar incidentes de plataforma para o Squad de Engenharia."],
                    ),
                    SurfaceRoleOverlayGuide(
                        overlay="strategist_versus",
                        title="Strategist Versus",
                        harness_key="harness_strategist_versus_v1",
                        primary_domains=["strategy", "projects", "meetings", "governance"],
                        recommended_actions=["discover", "read", "analyze", "update"],
                        escalation_rules=["Escalar finanças para finance_versus.", "Escalar execução/cadência para pmo_controller_versus."],
                    ),
                    SurfaceRoleOverlayGuide(
                        overlay="pmo_controller_versus",
                        title="PMO Controller Versus",
                        harness_key="harness_pmo_controller_versus_v1",
                        primary_domains=["routine", "projects", "processes", "meetings", "governance"],
                        recommended_actions=["discover", "read", "analyze", "update"],
                        escalation_rules=["Escalar estratégia para strategist_versus.", "Escalar incidentes para Engenharia."],
                    ),
                    SurfaceRoleOverlayGuide(
                        overlay="business_architect_versus",
                        title="Business Architect Versus",
                        harness_key="harness_business_architect_versus_v1",
                        primary_domains=["processes", "routine", "projects", "strategy", "governance"],
                        recommended_actions=["discover", "read", "analyze", "update"],
                        escalation_rules=["Escalar boundary técnico para Arquiteto de Engenharia.", "Escalar controladoria para finance_versus."],
                    ),
                    SurfaceRoleOverlayGuide(
                        overlay="operations_versus",
                        title="Operations Versus",
                        harness_key="harness_operations_versus_v1",
                        primary_domains=["routine", "projects", "processes", "meetings"],
                        recommended_actions=["discover", "read", "analyze", "update"],
                        escalation_rules=["Não usar ops como atalho.", "Escalar plataforma para Engenharia."],
                    ),
                    SurfaceRoleOverlayGuide(
                        overlay="followup_collector_versus",
                        title="Follow-up Collector Versus",
                        harness_key="harness_followup_collector_versus_v1",
                        primary_domains=["routine", "projects", "meetings", "governance"],
                        recommended_actions=["discover", "read", "analyze", "update"],
                        escalation_rules=["Escalar estratégia para Strategist/PMO.", "Escalar financeiro para Finance Versus."],
                    ),
                    SurfaceRoleOverlayGuide(
                        overlay="finance_versus",
                        title="Finance Versus",
                        harness_key="harness_finance_versus_v1",
                        primary_domains=["finance", "strategy", "governance"],
                        recommended_actions=["discover", "read", "analyze", "update"],
                        escalation_rules=["Manter gate humano em mutações financeiras.", "Escalar auditoria independente para auditor_versus."],
                    ),
                    SurfaceRoleOverlayGuide(
                        overlay="arquiteto_engenharia",
                        title="Arquiteto de Engenharia",
                        harness_key="harness_arquiteto_engenharia_v1",
                        primary_domains=["governance", "identity_admin", "analytics", "strategy"],
                        recommended_actions=["discover", "read", "analyze", "audit", "update"],
                        escalation_rules=["Escalar intervenção runtime para ops.", "Manter foco em boundary e segurança."],
                    ),
                    SurfaceRoleOverlayGuide(
                        overlay="backend_api_engenharia",
                        title="Backend API de Engenharia",
                        harness_key="harness_backend_api_engenharia_v1",
                        primary_domains=["governance", "identity_admin", "analytics", "strategy"],
                        recommended_actions=["discover", "read", "analyze", "audit", "update"],
                        escalation_rules=["Escalar regras de negócio para Backend Service.", "Escalar auth/OAuth crítico para Arquiteto."],
                    ),
                    SurfaceRoleOverlayGuide(
                        overlay="ai_engineer_engenharia",
                        title="AI Engineer de Engenharia",
                        harness_key="harness_ai_engineer_engenharia_v1",
                        primary_domains=["governance", "analytics", "strategy", "identity_admin"],
                        recommended_actions=["discover", "read", "analyze", "audit", "update"],
                        escalation_rules=["Escalar boundary para Arquiteto.", "Escalar incidente runtime para Coordenador/ops."],
                    ),
                ],
            ),
            SurfacePlaybook(
                surface="analytics",
                title="Playbook MCP Analytics",
                objective="Executar leituras analíticas tenant-safe sem mutar dados operacionais.",
                actor_roles=["administrador", "admin_tecnico"],
                allowed_domains=["analytics", "strategy", "real_estate_auctions", "finance", "workload"],
                default_scope="explicit_company_id",
                discovery_tools=["list_analytics_app32_capabilities", "describe_app32_crud_contracts_tool"],
                startup_checklist=[
                    "Confirmar company_id explícito ou empresa alvo da análise.",
                    "Ler capabilities analytics e limitar-se a operações de leitura/análise.",
                    "Se a pergunta exigir mutação, redirecionar para a surface apropriada.",
                ],
                interaction_rules=[
                    SurfaceInteractionRule(
                        rule="Executar apenas operações read/list/analyze.",
                        rationale="A surface analytics existe para leitura segura e não para mutação.",
                    ),
                    SurfaceInteractionRule(
                        rule="Responder com base em filtros tenant-safe e sem extrapolar dados de outras empresas.",
                        rationale="Preserva isolamento multi-tenant durante análises cruzadas.",
                    ),
                ],
                forbidden_actions=[
                    "Nunca mutar dados operacionais ou financeiros pela surface analytics.",
                    "Não usar tools de admin ou user para contornar ausência de permissão analítica.",
                ],
                example_flows=[
                    SurfaceExampleFlow(
                        title="Diagnóstico estratégico",
                        steps=[
                            "Ler capabilities analytics.",
                            "Consultar contrato strategy.",
                            "Executar get_plan_diagnostics apenas como leitura.",
                        ],
                    )
                ],
                role_overlays=[
                    SurfaceRoleOverlayGuide(
                        overlay="performance_analyst_versus",
                        title="Performance Analyst Versus",
                        harness_key="harness_performance_analyst_versus_v1",
                        primary_domains=["analytics", "strategy", "workload"],
                        recommended_actions=["discover", "read", "analyze"],
                        escalation_rules=["Escalar mutação para Strategist/Coordenador Versus.", "Escalar finanças para Finance Versus."],
                    ),
                    SurfaceRoleOverlayGuide(
                        overlay="auditor_versus",
                        title="Auditor Versus",
                        harness_key="harness_auditor_versus_v1",
                        primary_domains=["analytics", "finance", "strategy", "governance", "workload"],
                        recommended_actions=["discover", "read", "analyze", "audit"],
                        escalation_rules=["Não mutar; apenas recomendar correções.", "Escalar correção para Versus ou Engenharia conforme o achado."],
                    ),
                    SurfaceRoleOverlayGuide(
                        overlay="dba_engenharia",
                        title="DBA de Engenharia",
                        harness_key="harness_dba_engenharia_v1",
                        primary_domains=["analytics", "workload", "governance", "strategy"],
                        recommended_actions=["discover", "read", "analyze", "audit"],
                        escalation_rules=["Não usar SQL livre fora do contrato.", "Escalar mudança estrutural para Coordenador/Arquiteto."],
                    ),
                ],
            ),
            SurfacePlaybook(
                surface="ops",
                title="Playbook MCP Ops",
                objective="Executar ações de suporte operacional, incidentes e orquestração de intervenção com mínimo escopo.",
                actor_roles=["admin_tecnico"],
                allowed_domains=["operations", "routine", "processes", "projects", "meetings", "workload"],
                default_scope="active_company",
                discovery_tools=["list_ops_app32_capabilities", "describe_app32_crud_contracts_tool"],
                startup_checklist=[
                    "Confirmar se o caso é incidente operacional ou intervenção suportada pela surface ops.",
                    "Verificar company_id ativo e contexto do chamado/tarefa.",
                    "Ler capabilities ops antes de abrir ou atualizar intervenção.",
                ],
                interaction_rules=[
                    SurfaceInteractionRule(
                        rule="Escalonar incidentes via trilha oficial de intervenção e não por mutações paralelas.",
                        rationale="Mantém observabilidade e fluxo operacional uniforme.",
                    ),
                    SurfaceInteractionRule(
                        rule="Separar claramente suporte operacional de análise e de administração geral.",
                        rationale="Reduz mistura conceitual entre ops, analytics e admin.",
                    ),
                ],
                forbidden_actions=[
                    "Não executar analytics amplas ou consultas livres fora da surface adequada.",
                    "Não usar ops para mutações financeiras sensíveis.",
                ],
                example_flows=[
                    SurfaceExampleFlow(
                        title="Escalonar incidente técnico",
                        steps=[
                            "Ler capabilities ops.",
                            "Validar contexto e tenant ativo.",
                            "Executar a tool oficial de escalonamento/intervenção.",
                        ],
                    )
                ],
                role_overlays=[
                    SurfaceRoleOverlayGuide(
                        overlay="coordenador_engenharia",
                        title="Coordenador do Squad de Engenharia",
                        harness_key="harness_coordenador_engenharia_v1",
                        primary_domains=["operations", "routine", "processes", "projects", "meetings", "workload", "governance"],
                        recommended_actions=["discover", "read", "analyze", "audit", "update"],
                        escalation_rules=["Roteia para especialista técnico adequado.", "Não operar o negócio como cliente/consultoria."],
                    ),
                    SurfaceRoleOverlayGuide(
                        overlay="frontend_engenharia",
                        title="Frontend de Engenharia",
                        harness_key="harness_frontend_engenharia_v1",
                        primary_domains=["operations", "routine", "projects", "meetings"],
                        recommended_actions=["discover", "read", "analyze", "audit", "update"],
                        escalation_rules=["Escalar contracts para Backend API.", "Escalar boundary para Arquiteto."],
                    ),
                    SurfaceRoleOverlayGuide(
                        overlay="backend_service_engenharia",
                        title="Backend Service de Engenharia",
                        harness_key="harness_backend_service_engenharia_v1",
                        primary_domains=["operations", "routine", "processes", "projects", "meetings", "governance"],
                        recommended_actions=["discover", "read", "analyze", "audit", "update"],
                        escalation_rules=["Escalar performance SQL para DBA.", "Escalar contracts para Backend API."],
                    ),
                    SurfaceRoleOverlayGuide(
                        overlay="qa_automation_engenharia",
                        title="QA Automation de Engenharia",
                        harness_key="harness_qa_automation_engenharia_v1",
                        primary_domains=["operations", "routine", "processes", "projects", "meetings", "workload", "governance"],
                        recommended_actions=["discover", "read", "analyze", "audit", "update"],
                        escalation_rules=["Escalar correção ao especialista apropriado.", "Usar analytics/admin apenas quando o caso exigir investigação complementar."],
                    ),
                ],
            ),
        ]
    )


APP32_SURFACE_PLAYBOOKS_MANIFEST = build_surface_playbooks_manifest()


__all__ = [
    "APP32_SURFACE_PLAYBOOKS_MANIFEST",
    "PlaybookRole",
    "PlaybookSurface",
    "SurfaceExampleFlow",
    "SurfaceInteractionRule",
    "SurfaceRoleOverlayGuide",
    "SurfacePlaybook",
    "SurfacePlaybooksEnvelope",
    "SurfacePlaybooksManifest",
    "build_surface_playbooks_manifest",
]
