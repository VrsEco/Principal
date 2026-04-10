from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from .base import MCPSuccessEnvelope, _StrictModel


PlaybookSurface = Literal["user", "admin", "analytics", "ops"]
PlaybookRole = Literal["colaborador", "cliente", "administrador", "admin_tecnico"]


class SurfaceInteractionRule(_StrictModel):
    rule: str = Field(min_length=8, max_length=320)
    rationale: str = Field(min_length=8, max_length=320)


class SurfaceExampleFlow(_StrictModel):
    title: str = Field(min_length=4, max_length=140)
    steps: list[str] = Field(default_factory=list, min_length=1)


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

    @model_validator(mode="after")
    def _validate_surface_rules(self):
        if self.surface == "analytics" and self.default_scope == "none":
            raise ValueError("Surface analytics deve operar com escopo explícito ou empresa ativa.")
        if self.surface == "user" and "finance" in self.allowed_domains:
            raise ValueError("Surface user não deve expor domínio financeiro sensível.")
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
                objective="Executar fluxos operacionais do usuário final com escopo tenant-safe e menor privilégio.",
                actor_roles=["colaborador", "cliente", "administrador"],
                allowed_domains=["routine", "projects", "meetings", "strategy"],
                default_scope="active_company",
                discovery_tools=["list_user_app32_capabilities", "describe_app32_crud_contracts_tool"],
                startup_checklist=[
                    "Confirmar company_id ativo antes de qualquer leitura ou mutação.",
                    "Consultar as capabilities da surface user e o contrato CRUD do domínio alvo.",
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
                    "Não executar mutações financeiras sensíveis pela surface user.",
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
            ),
            SurfacePlaybook(
                surface="admin",
                title="Playbook MCP Admin",
                objective="Executar operações administrativas explícitas com governança, auditoria e gates humanos.",
                actor_roles=["administrador", "admin_tecnico"],
                allowed_domains=["routine", "projects", "meetings", "finance", "strategy", "governance"],
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
            ),
            SurfacePlaybook(
                surface="analytics",
                title="Playbook MCP Analytics",
                objective="Executar leituras analíticas tenant-safe sem mutar dados operacionais.",
                actor_roles=["administrador", "admin_tecnico"],
                allowed_domains=["analytics", "strategy", "finance", "workload"],
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
            ),
            SurfacePlaybook(
                surface="ops",
                title="Playbook MCP Ops",
                objective="Executar ações de suporte operacional, incidentes e orquestração de intervenção com mínimo escopo.",
                actor_roles=["admin_tecnico"],
                allowed_domains=["operations", "routine", "projects", "meetings"],
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
    "SurfacePlaybook",
    "SurfacePlaybooksEnvelope",
    "SurfacePlaybooksManifest",
    "build_surface_playbooks_manifest",
]
