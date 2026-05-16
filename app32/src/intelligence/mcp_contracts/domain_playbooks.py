from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from .base import MCPSuccessEnvelope, _StrictModel
from .profiles import MCPAllowedSurface, MCPOverlayName, MCPProfileName


DomainPlaybookName = Literal[
    "routine",
    "processes",
    "projects",
    "meetings",
    "strategy",
    "finance",
    "analytics",
    "workload",
    "identity_self_service",
    "identity_admin",
    "operations",
    "governance",
]


class DomainPromptPolicy(_StrictModel):
    system_preamble: str = Field(min_length=24, max_length=800)
    required_context: list[str] = Field(default_factory=list, min_length=1)
    planning_rules: list[str] = Field(default_factory=list, min_length=2)
    refusal_rules: list[str] = Field(default_factory=list, min_length=1)
    output_contract: str = Field(min_length=16, max_length=500)


class DomainPlaybook(_StrictModel):
    """Playbook canônico por domínio de negócio para agentes IA/MCP."""

    domain: DomainPlaybookName
    aliases: list[str] = Field(default_factory=list)
    title: str = Field(min_length=6, max_length=140)
    objective: str = Field(min_length=16, max_length=500)
    allowed_surfaces: list[MCPAllowedSurface] = Field(default_factory=list, min_length=1)
    allowed_profiles: list[MCPProfileName] = Field(default_factory=list, min_length=1)
    allowed_role_overlays: list[MCPOverlayName] = Field(default_factory=list)
    canonical_tools: list[str] = Field(default_factory=list, min_length=1)
    canonical_artifacts: list[str] = Field(default_factory=list, min_length=1)
    discovery_sequence: list[str] = Field(default_factory=list, min_length=2)
    prompt_policy: DomainPromptPolicy
    analysis_rules: list[str] = Field(default_factory=list, min_length=1)
    forbidden_shortcuts: list[str] = Field(default_factory=list, min_length=1)
    escalation_rules: list[str] = Field(default_factory=list, min_length=1)
    tenant_scope_required: bool = True
    sql_freeform_allowed: bool = False

    @model_validator(mode="after")
    def _validate_domain_playbook(self):
        if not self.tenant_scope_required:
            raise ValueError("Playbook de domínio MCP exige tenant_scope_required=True.")
        if self.sql_freeform_allowed:
            raise ValueError("Playbook de domínio MCP não pode liberar SQL livre.")
        if "company_id" not in self.prompt_policy.required_context:
            raise ValueError("Playbook de domínio MCP deve exigir company_id.")
        if self.domain == "analytics" and "analytics" not in self.allowed_surfaces:
            raise ValueError("Playbook analytics deve permitir a surface analytics.")
        if self.domain == "operations" and self.allowed_profiles != ["admin_tecnico"]:
            raise ValueError("Playbook operations deve ficar restrito ao perfil admin_tecnico.")
        if self.domain == "identity_admin" and "user" in self.allowed_surfaces:
            raise ValueError("Playbook identity_admin não deve expor surface user.")
        return self


class DomainPlaybooksManifest(_StrictModel):
    version: str = Field(default="app32.mcp.domain-playbooks.v1", min_length=1, max_length=80)
    playbooks: list[DomainPlaybook] = Field(default_factory=list, min_length=1)

    def get_domain(self, domain: DomainPlaybookName | str) -> DomainPlaybook | None:
        normalized = str(domain or "").strip().lower()
        for playbook in self.playbooks:
            if playbook.domain == normalized or normalized in playbook.aliases:
                return playbook
        return None


DomainPlaybooksEnvelope = MCPSuccessEnvelope[DomainPlaybooksManifest | DomainPlaybook]


def _prompt_policy(
    *,
    preamble: str,
    output_contract: str,
    required_context: list[str] | None = None,
    planning_rules: list[str] | None = None,
    refusal_rules: list[str] | None = None,
) -> DomainPromptPolicy:
    return DomainPromptPolicy(
        system_preamble=preamble,
        required_context=required_context or ["company_id", "user_id", "surface", "profile"],
        planning_rules=planning_rules
        or [
            "Descobrir capabilities e contrato do domínio antes de executar a ação.",
            "Confirmar escopo, permissões e risco antes de qualquer mutação.",
        ],
        refusal_rules=refusal_rules
        or [
            "Recusar SQL livre, acesso cross-tenant e ação fora da surface/perfil autorizado.",
        ],
        output_contract=output_contract,
    )


def build_domain_playbooks_manifest() -> DomainPlaybooksManifest:
    return DomainPlaybooksManifest(
        playbooks=[
            DomainPlaybook(
                domain="routine",
                aliases=["tasks", "work", "worklog"],
                title="Playbook de Rotinas",
                objective="Guiar agentes em processos, rotinas recorrentes e tarefas operacionais do dia a dia.",
                allowed_surfaces=["user", "admin", "ops"],
                allowed_profiles=["colaborador", "cliente", "administrador", "admin_tecnico"],
                allowed_role_overlays=["coordenador_cliente", "comercial_cliente", "operacional_cliente", "pessoas_capacidade_cliente", "coordenador_versus", "pmo_controller_versus", "business_architect_versus", "operations_versus", "followup_collector_versus", "coordenador_engenharia", "frontend_engenharia", "backend_service_engenharia", "qa_automation_engenharia"],
                canonical_tools=["describe_app32_crud_contracts_tool", "list_app32_capabilities"],
                canonical_artifacts=["src.intelligence.mcp_contracts.crud_domains", "src.intelligence.tool_catalog"],
                discovery_sequence=["list_app32_capabilities", "describe_app32_crud_contracts_tool", "executar tool operacional permitida"],
                prompt_policy=_prompt_policy(
                    preamble="Você opera rotinas do APP32 com foco em execução segura, escopo da empresa ativa e trilha auditável.",
                    output_contract="Responder com ação pretendida, parâmetros confirmados, resultado e pendências de confirmação quando houver risco.",
                ),
                analysis_rules=["Usar analytics apenas quando a rotina exigir leitura consolidada e nunca por consulta livre."],
                forbidden_shortcuts=["Não inferir company_id por nome parcial de empresa.", "Não criar tarefas/processos sem contrato CRUD válido."],
                escalation_rules=["Escalar para admin/ops quando a rotina exigir privilégio técnico ou alteração sensível."],
            ),
            DomainPlaybook(
                domain="processes",
                aliases=["process", "workflow"],
                title="Playbook de Processos",
                objective="Orientar execução e consulta de processos com contrato explícito e rastreabilidade por empresa.",
                allowed_surfaces=["user", "admin", "ops"],
                allowed_profiles=["colaborador", "cliente", "administrador", "admin_tecnico"],
                allowed_role_overlays=["coordenador_cliente", "operacional_cliente", "coordenador_versus", "pmo_controller_versus", "business_architect_versus", "operations_versus", "coordenador_engenharia", "backend_service_engenharia", "qa_automation_engenharia"],
                canonical_tools=["describe_app32_crud_contracts_tool", "list_app32_capabilities"],
                canonical_artifacts=["src.intelligence.mcp_contracts.crud_domains", "src.intelligence.tooling.capabilities"],
                discovery_sequence=["list_app32_capabilities", "describe_app32_crud_contracts_tool", "validar escopo do processo"],
                prompt_policy=_prompt_policy(
                    preamble="Você atua em processos do APP32 com escopo de empresa, estado do workflow e evidência da ação.",
                    output_contract="Responder com processo-alvo, estado, próximos passos, filtros e confirmação exigida quando houver mutação.",
                ),
                analysis_rules=["Consolidar processos por read model/capability permitida; não cruzar tenants."],
                forbidden_shortcuts=["Não saltar etapas do processo sem gate.", "Não assumir ownership sem vínculo no tenant."],
                escalation_rules=["Encaminhar exceções operacionais para ops e alterações administrativas para admin."],
            ),
            DomainPlaybook(
                domain="projects",
                title="Playbook de Projetos",
                objective="Orientar CRUD e análises de projetos, atividades, prazos, responsáveis e riscos de execução.",
                allowed_surfaces=["user", "admin", "analytics", "ops"],
                allowed_profiles=["colaborador", "cliente", "administrador", "admin_tecnico"],
                allowed_role_overlays=["coordenador_cliente", "comercial_cliente", "operacional_cliente", "estrategico_cliente", "pessoas_capacidade_cliente", "coordenador_versus", "strategist_versus", "pmo_controller_versus", "business_architect_versus", "operations_versus", "performance_analyst_versus", "coordenador_engenharia", "frontend_engenharia", "backend_service_engenharia", "qa_automation_engenharia"],
                canonical_tools=["describe_app32_crud_contracts_tool", "get_projects_execution_risk_read_model"],
                canonical_artifacts=["src.intelligence.mcp_contracts.crud_domains", "services.analytics_read_model_service"],
                discovery_sequence=["list_app32_capabilities", "describe_app32_crud_contracts_tool", "get_projects_execution_risk_read_model quando for análise"],
                prompt_policy=_prompt_policy(
                    preamble="Você atua no domínio de projetos do APP32 preservando tenant, responsável, prazo e rastreabilidade.",
                    output_contract="Separar leitura, análise e mutação; listar filtros usados e identificar se há gate humano necessário.",
                ),
                analysis_rules=["Análises de projeto devem usar read model whitelisted e envelope de grounding quando disponíveis."],
                forbidden_shortcuts=["Não alterar status/prazo sem contrato e permissão.", "Não misturar projetos de empresas diferentes."],
                escalation_rules=["Usar analytics para diagnóstico e admin/ops apenas quando a ação exigir privilégio maior."],
            ),
            DomainPlaybook(
                domain="meetings",
                title="Playbook de Reuniões",
                objective="Guiar agentes em pauta, registro, encaminhamentos e acompanhamento de reuniões.",
                allowed_surfaces=["user", "admin", "ops"],
                allowed_profiles=["colaborador", "cliente", "administrador", "admin_tecnico"],
                allowed_role_overlays=["coordenador_cliente", "comercial_cliente", "operacional_cliente", "admfin_cliente", "estrategico_cliente", "pessoas_capacidade_cliente", "coordenador_versus", "strategist_versus", "pmo_controller_versus", "business_architect_versus", "operations_versus", "followup_collector_versus", "finance_versus"],
                canonical_tools=["describe_app32_crud_contracts_tool", "list_app32_capabilities"],
                canonical_artifacts=["src.intelligence.mcp_contracts.crud_domains"],
                discovery_sequence=["list_app32_capabilities", "describe_app32_crud_contracts_tool", "validar reunião e participantes"],
                prompt_policy=_prompt_policy(
                    preamble="Você opera reuniões do APP32 com foco em contexto, participantes, encaminhamentos e escopo de tenant.",
                    output_contract="Responder com reunião-alvo, decisões, tarefas geradas e próximos passos auditáveis.",
                ),
                analysis_rules=["Resumir decisões apenas a partir de dados da reunião no tenant ativo."],
                forbidden_shortcuts=["Não expor participantes de outra empresa.", "Não gerar encaminhamento sem reunião/contexto confirmados."],
                escalation_rules=["Escalar conflitos de permissão ou reunião multiempresa para administrador."],
            ),
            DomainPlaybook(
                domain="strategy",
                title="Playbook de Estratégia",
                objective="Orientar leitura e evolução de planos, seções, diagnósticos e indicadores estratégicos.",
                allowed_surfaces=["user", "admin", "analytics"],
                allowed_profiles=["colaborador", "cliente", "administrador", "admin_tecnico"],
                allowed_role_overlays=["coordenador_cliente", "comercial_cliente", "admfin_cliente", "estrategico_cliente", "coordenador_versus", "strategist_versus", "pmo_controller_versus", "business_architect_versus", "operations_versus", "performance_analyst_versus", "finance_versus", "auditor_versus", "coordenador_engenharia", "arquiteto_engenharia", "backend_api_engenharia", "ai_engineer_engenharia", "dba_engenharia"],
                canonical_tools=["describe_app32_crud_contracts_tool", "get_plan_diagnostics_read_model"],
                canonical_artifacts=["src.intelligence.mcp_contracts.analysis_catalog", "services.analytics_read_model_service"],
                discovery_sequence=["describe_app32_allowed_analyses_tool", "get_plan_diagnostics_read_model", "se houver mutação, redirecionar para contrato CRUD"],
                prompt_policy=_prompt_policy(
                    preamble="Você apoia estratégia no APP32 com linguagem executiva, evidências e fronteira clara entre insight e mutação.",
                    output_contract="Responder com diagnóstico, evidências, lacunas, riscos e recomendações sem inventar métricas.",
                ),
                analysis_rules=["Usar analysis_id strategy_plan_diagnostics quando aplicável; não inventar score fora do envelope."],
                forbidden_shortcuts=["Não extrapolar indicadores não retornados por read model.", "Não alterar plano por surface analytics."],
                escalation_rules=["Quando a recomendação exigir alteração de plano, redirecionar para user/admin com confirmação."],
            ),
            DomainPlaybook(
                domain="finance",
                title="Playbook de Finanças",
                objective="Guiar leituras e ações financeiras com rastreabilidade, company_id explícito e aderência às mesmas permissões que a senha do usuário já possui no APP32.",
                allowed_surfaces=["user", "admin", "analytics"],
                allowed_profiles=["colaborador", "administrador", "admin_tecnico"],
                allowed_role_overlays=["admfin_cliente", "coordenador_versus", "strategist_versus", "pmo_controller_versus", "finance_versus", "auditor_versus"],
                canonical_tools=["describe_app32_crud_contracts_tool", "describe_app32_allowed_analyses_tool"],
                canonical_artifacts=["src.intelligence.mcp_contracts.analysis_catalog", "src.intelligence.security.tool_policy"],
                discovery_sequence=["describe_app32_profile_contracts_tool", "list_user_app32_capabilities", "validar permissão financeira efetiva, risco e gate humano quando exigido"],
                prompt_policy=_prompt_policy(
                    preamble="Você trata finanças do APP32 como domínio sensível e permission-aware: só execute o que o usuário já pode fazer no APP32, sempre com company_id explícito e sem SQL livre.",
                    output_contract="Responder com filtros financeiros usados, permissões assumidas, limitações, risco, necessidade de gate humano quando houver e resultado permitido.",
                ),
                analysis_rules=["Usar apenas tools e análises financeiras permitidas ao usuário/empresa ativos; SQL livre e credenciais são proibidos."],
                forbidden_shortcuts=["Não executar ação financeira que a senha do usuário não possua no APP32.", "Não expor credenciais bancárias ou dados cross-tenant."],
                escalation_rules=["Exigir confirmação humana quando a policy marcar gate para risco high/critical ou exclusão financeira."],
            ),
            DomainPlaybook(
                domain="analytics",
                title="Playbook de Analytics",
                objective="Padronizar análises por read models whitelisted e envelopes com grounding.",
                allowed_surfaces=["analytics", "ops"],
                allowed_profiles=["administrador", "admin_tecnico"],
                allowed_role_overlays=["performance_analyst_versus", "auditor_versus", "arquiteto_engenharia", "backend_api_engenharia", "ai_engineer_engenharia", "dba_engenharia"],
                canonical_tools=["describe_app32_allowed_analyses_tool", "get_plan_diagnostics_read_model"],
                canonical_artifacts=["src.intelligence.mcp_contracts.analysis_envelopes", "services.analytics_read_model_service"],
                discovery_sequence=["describe_app32_allowed_analyses_tool", "executar read model whitelisted", "responder com envelope/grounding"],
                prompt_policy=_prompt_policy(
                    preamble="Você executa analytics do APP32 apenas por catálogo permitido, read models whitelisted e envelope com grounding.",
                    output_contract="Responder com analysis_id, filtros, row_count, limitações, evidências e sem mutações.",
                ),
                analysis_rules=["Toda resposta analítica deve declarar filtros, limitações, origem e proibição de mutação."],
                forbidden_shortcuts=["Não mutar dados por analytics.", "Não gerar SQL livre.", "Não cruzar tenants sem autorização explícita de sistema."],
                escalation_rules=["Se faltar read model permitido, sugerir abertura de atividade de engenharia em vez de improvisar consulta."],
            ),
            DomainPlaybook(
                domain="workload",
                aliases=["capacity", "team_capacity"],
                title="Playbook de Carga e Capacidade",
                objective="Guiar leitura de workload, capacidade de equipe e sinais de sobrecarga com filtros tenant-safe.",
                allowed_surfaces=["analytics", "ops"],
                allowed_profiles=["administrador", "admin_tecnico"],
                canonical_tools=["describe_app32_allowed_analyses_tool", "get_team_workload_read_model"],
                canonical_artifacts=["src.intelligence.mcp_contracts.analysis_catalog", "services.analytics_read_model_service"],
                discovery_sequence=["describe_app32_allowed_analyses_tool", "get_team_workload_read_model", "responder com limites e filtros"],
                prompt_policy=_prompt_policy(
                    preamble="Você analisa workload do APP32 por equipe, período e empresa explícita, sem alterar alocações.",
                    output_contract="Responder com equipe, período, filtros, sinais de sobrecarga, limitações e próximos passos seguros.",
                ),
                analysis_rules=["Usar analysis_id workload_team_capacity e nunca ajustar alocação pela surface analytics."],
                forbidden_shortcuts=["Não reatribuir trabalho durante análise.", "Não comparar equipes de empresas diferentes."],
                escalation_rules=["Escalar replanejamento para admin/ops com confirmação humana."],
            ),
            DomainPlaybook(
                domain="operations",
                title="Playbook de Operações",
                objective="Guiar incidentes, suporte técnico e intervenções com rastreabilidade operacional.",
                allowed_surfaces=["ops"],
                allowed_profiles=["admin_tecnico"],
                allowed_role_overlays=["coordenador_engenharia", "frontend_engenharia", "backend_service_engenharia", "qa_automation_engenharia"],
                canonical_tools=["list_ops_app32_capabilities", "describe_app32_surface_playbooks_tool"],
                canonical_artifacts=["src.intelligence.mcp_contracts.playbooks", "src.intelligence.audit"],
                discovery_sequence=["list_ops_app32_capabilities", "describe_app32_surface_playbooks_tool", "registrar intervenção quando aplicável"],
                prompt_policy=_prompt_policy(
                    preamble="Você atua em operações do APP32 como suporte técnico, sem contornar admin/analytics e sempre com trilha auditável.",
                    output_contract="Responder com incidente/ação, escopo, impacto, evidência, próxima checagem e rollback quando aplicável.",
                ),
                analysis_rules=["Análises operacionais devem permanecer em ops/analytics e não substituir auditoria de produção."],
                forbidden_shortcuts=["Não usar ops para análise financeira ampla.", "Não executar alteração sem escopo e evidência."],
                escalation_rules=["Escalar impacto produtivo para release/engenharia e registrar intervenção."],
            ),
            DomainPlaybook(
                domain="identity_self_service",
                aliases=["identity", "my_profile", "my_companies", "my_contacts"],
                title="Playbook de Identidade Self-Service",
                objective="Padronizar leitura e atualização de dados próprios do usuário sem promover acesso administrativo.",
                allowed_surfaces=["user", "admin"],
                allowed_profiles=["colaborador", "cliente", "administrador", "admin_tecnico"],
                allowed_role_overlays=["coordenador_cliente", "comercial_cliente", "operacional_cliente", "admfin_cliente", "estrategico_cliente", "pessoas_capacidade_cliente"],
                canonical_tools=["list_user_app32_capabilities", "describe_app32_profile_contracts_tool"],
                canonical_artifacts=["src.intelligence.mcp_contracts.profiles", "src.intelligence.security.tool_policy"],
                discovery_sequence=["describe_app32_profile_contracts_tool", "list_user_app32_capabilities", "validar self-service do próprio usuário"],
                prompt_policy=_prompt_policy(
                    preamble="Você interpreta self-service de identidade do APP32 com foco em dados do próprio usuário, tenant obrigatório e menor privilégio.",
                    output_contract="Responder com ação self-service, dados próprios envolvidos, escopo confirmado e limites administrativos aplicáveis.",
                ),
                analysis_rules=["Expor apenas dados do próprio usuário e de empresas já vinculadas ao principal."],
                forbidden_shortcuts=["Não listar usuários do sistema por self-service.", "Não alterar perfil/permissão por surface user."],
                escalation_rules=["Escalar para admin quando o pedido envolver gestão de acesso de terceiros ou mudança de perfil."],
            ),
            DomainPlaybook(
                domain="identity_admin",
                aliases=["identity_access", "profiles", "users", "permissions"],
                title="Playbook de Identidade Administrativa",
                objective="Padronizar leitura e mutação administrativa de perfis, permissões e acesso de usuários do sistema.",
                allowed_surfaces=["admin"],
                allowed_profiles=["administrador", "admin_tecnico"],
                allowed_role_overlays=["coordenador_versus", "strategist_versus", "pmo_controller_versus", "business_architect_versus", "operations_versus", "finance_versus", "arquiteto_engenharia", "backend_api_engenharia", "ai_engineer_engenharia"],
                canonical_tools=["describe_app32_profile_contracts_tool", "list_admin_app32_capabilities"],
                canonical_artifacts=["src.intelligence.mcp_contracts.profiles", "src.intelligence.security.tool_policy"],
                discovery_sequence=["describe_app32_profile_contracts_tool", "list_admin_app32_capabilities", "validar menor privilégio administrativo"],
                prompt_policy=_prompt_policy(
                    preamble="Você interpreta identidade e permissões do APP32 com menor privilégio, tenant obrigatório e auditoria.",
                    output_contract="Responder com perfil, surfaces permitidas, domínios autorizados, risco e bloqueios aplicáveis.",
                ),
                analysis_rules=["Não expor dados de identidade além do necessário para decisão de permissão."],
                forbidden_shortcuts=["Não promover usuário/perfil sem contrato e confirmação.", "Não usar user surface para administração de acesso."],
                escalation_rules=["Escalar exceções de permissão para admin_tecnico e registrar justificativa."],
            ),
            DomainPlaybook(
                domain="governance",
                aliases=["policy", "mcp_policy"],
                title="Playbook de Governança MCP",
                objective="Consolidar políticas, perfis, surfaces, permissões e critérios de auditoria para agentes externos.",
                allowed_surfaces=["admin", "analytics", "ops"],
                allowed_profiles=["administrador", "admin_tecnico"],
                allowed_role_overlays=["coordenador_versus", "strategist_versus", "pmo_controller_versus", "business_architect_versus", "operations_versus", "performance_analyst_versus", "finance_versus", "auditor_versus", "coordenador_engenharia", "arquiteto_engenharia", "backend_api_engenharia", "backend_service_engenharia", "ai_engineer_engenharia", "dba_engenharia", "qa_automation_engenharia"],
                canonical_tools=["describe_app32_profile_contracts_tool", "describe_app32_surface_playbooks_tool"],
                canonical_artifacts=["src.intelligence.mcp_contracts.profiles", "src.intelligence.mcp_contracts.playbooks"],
                discovery_sequence=["describe_app32_profile_contracts_tool", "describe_app32_surface_playbooks_tool", "confrontar contrato de domínio"],
                prompt_policy=_prompt_policy(
                    preamble="Você interpreta governança MCP do APP32 como fonte de verdade para perfis, escopo, surface e permissões.",
                    output_contract="Responder com decisão de acesso, contrato consultado, razão, escopo e ação segura recomendada.",
                ),
                analysis_rules=["Usar contratos MCP como fonte de verdade; divergências viram atividade de engenharia."],
                forbidden_shortcuts=["Não elevar perfil sem contrato.", "Não criar nova surface sem manifesto e testes."],
                escalation_rules=["Escalar exceções de acesso para revisão técnica e registro auditável."],
            ),
        ]
    )


APP32_DOMAIN_PLAYBOOKS_MANIFEST = build_domain_playbooks_manifest()


__all__ = [
    "APP32_DOMAIN_PLAYBOOKS_MANIFEST",
    "DomainPlaybook",
    "DomainPlaybookName",
    "DomainPlaybooksEnvelope",
    "DomainPlaybooksManifest",
    "DomainPromptPolicy",
    "build_domain_playbooks_manifest",
]
