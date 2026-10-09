"""Coortes de leitura do mcp-versus por domínio (SPEC classificacao_dominios_mcp_versus_v1).

Cada domínio publica um conjunto fixo de leituras, revisadas pelo contrato automático
(``mcp_cohort_contract``). A publicação é controlada por UMA variável:

    MCP_VERSUS_READ_DOMAINS=strategy,processes,platform,commercial,finance

- **Ausente**: valem os assuntos NÃO sensíveis (``DEFAULT_ENABLED_DOMAINS``).
- **Definida**: vale exatamente a lista informada (acrescente ``commercial``/``finance`` para
  ligá-los). ``none`` (ou vazia) desliga todos: interruptor de emergência.

Assuntos fora da lista não são listados **nem registrados** (uma tool oculta mas
registrada seria invocável por quem conhecesse o nome). Comercial e financeiro carregam
dados sensíveis e nunca vêm ligados por padrão. A coorte de ``routine`` mantém a sua
flag própria (MCP_VERSUS_ROUTINE_READ_ENABLED).
"""
from __future__ import annotations

import os
from typing import Any, Iterable

ENV_DOMAINS = "MCP_VERSUS_READ_DOMAINS"
# Leituras de baixo risco e sem dados comerciais/financeiros: ligadas por padrão.
DEFAULT_ENABLED_DOMAINS = frozenset({"strategy", "processes", "platform", "knowledge"})

# domínio -> leituras publicáveis. Preenchido por domínio, cada nome validado pelo contrato.
READ_COHORT_TOOL_NAMES: dict[str, tuple[str, ...]] = {
    # strategy: identidade, alinhamento, planos, diagnósticos e jornada de estruturação
    "strategy": (
        "get_organizational_identity_tool",
        "get_plan_diagnostics_read_model",
        "get_process_strategic_profile_tool",
        "get_process_strategy_profile_tool",
        "get_strategic_alignment_n1_readiness_tool",
        "get_strategic_connection_graph",
        "get_strategic_connection_metrics",
        "get_strategy_alignment_n1_readiness_tool",
        "get_strategy_identity_tool",
        "get_structuring_journey_tool",
        "list_indicator_line_of_sight_tool",
        "list_plans",
        "list_process_strategy_alignment_links_tool",
    ),
    # processes: contexto de modelagem, melhoria e POP de processos
    "processes": (
        "get_process_improvement_analysis_context_tool",
        "get_process_modeling_package_tool",
        "get_process_pop_step_media_context_tool",
        "list_process_improvement_requests_tool",
    ),
    # knowledge: busca e resposta sobre o conhecimento organizacional de UMA empresa (ACL do RAG)
    "knowledge": (
        "answer_organizational_question_secure",
        "search_organizational_knowledge_secure",
    ),
    # platform: diagnóstico cadastral, carga da equipe e solicitações à Engenharia
    "platform": (
        "get_company_registration_diagnostics",
        "get_team_workload_read_model",
        "list_my_engineering_suggestions",
    ),
    # commercial: contratos, clientes, emissores, faturamento e catálogo comercial (dados sensíveis)
    "commercial": (
        "get_commercial_contract_workspace",
        "get_commercial_dashboard",
        "get_commercial_offer_contract_guidance",
        "get_commercial_product_service_readiness",
        "list_commercial_billing_queue",
        "list_commercial_billings_done",
        "list_commercial_catalog_structure",
        "list_commercial_contracts",
        "list_commercial_customer_portfolios",
        "list_commercial_customers",
        "list_commercial_fiscal_workspace",
        "list_commercial_issuers",
        "list_commercial_offer_process_candidates",
        "list_commercial_products_services",
    ),
    # finance: lançamentos, borderôs, orçamento, conciliação, classificação e relatórios (dados sensíveis)
    "finance": (
        "get_financial_bank_reconciliation_overview",
        "get_financial_bank_reconciliation_workspace",
        "get_financial_bordero",
        "get_financial_budget_execution_workspace",
        "get_financial_budget_matrix",
        "get_financial_budget_planning_workspace",
        "get_financial_classification_dashboard",
        "get_financial_entry",
        "get_financial_executive_dashboard",
        "get_financial_import_batch",
        "get_financial_payables_due_summary",
        "get_incentive_indicators",
        "list_financial_automation_executions",
        "list_financial_bank_reconciliation_candidates",
        "list_financial_borderos",
        "list_financial_budget_versions",
        "list_financial_classification_memories",
        "list_financial_classification_pending",
        "list_financial_classification_suggestions",
        "list_financial_domain_enablements",
        "list_financial_import_batches",
        "list_financial_ingestion_records",
        "list_financial_report_types",
        "list_financial_schedules",
    ),
}

# Prioridade do escopo de token usado para publicar a tool (somente os que os clientes recebem).
_SCOPE_PRIORITY = (("mcp_user", "mcp:user", "user"), ("mcp_analytics", "mcp:analytics", "analytics"), ("mcp_finance", "mcp:finance", "finance"))


def enabled_read_domains() -> frozenset[str]:
    raw = os.environ.get(ENV_DOMAINS)
    if raw is None:
        return DEFAULT_ENABLED_DOMAINS
    parts = {part.strip().lower() for part in raw.split(",") if part.strip()}
    return frozenset() if "none" in parts else frozenset(parts)


def all_read_cohort_names() -> tuple[str, ...]:
    return tuple(name for names in READ_COHORT_TOOL_NAMES.values() for name in names)


def enabled_read_cohort_names() -> tuple[str, ...]:
    enabled = enabled_read_domains()
    return tuple(name for domain, names in READ_COHORT_TOOL_NAMES.items() if domain in enabled for name in names)


def _scopes_of(capability: Any) -> Iterable[str]:
    return tuple(getattr(capability, "scopes", ()) or ())


def token_scope_for(capability: Any) -> str | None:
    """Escopo OAuth que o token precisa ter para a tool aparecer (None = inalcançável hoje)."""
    scopes = set(_scopes_of(capability))
    for catalog_scope, token_scope, _surface in _SCOPE_PRIORITY:
        if catalog_scope in scopes:
            return token_scope
    return None


def policy_surface_for(capability: Any) -> str:
    """Surface da política de execução, coerente com o escopo de token escolhido."""
    scopes = set(_scopes_of(capability))
    for catalog_scope, _token_scope, surface in _SCOPE_PRIORITY:
        if catalog_scope in scopes:
            return surface
    return "user"
