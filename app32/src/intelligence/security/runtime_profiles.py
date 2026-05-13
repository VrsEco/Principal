from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RuntimeHarnessSpec:
    key: str
    label: str
    business_role: str


@dataclass(frozen=True)
class RuntimeProfileSpec:
    key: str
    label: str
    default_surface: str
    actor_type: str
    allowed_surfaces: tuple[str, ...] = ()
    family_key: str | None = None
    family_label: str | None = None
    default_harness_key: str | None = None
    default_harness_label: str | None = None
    harnesses: tuple[RuntimeHarnessSpec, ...] = ()
    requires_training: bool = True
    supports_personal_token: bool = False


_RUNTIME_PROFILE_ALIASES = {
    "cliente": "squad_cliente",
    "client": "squad_cliente",
    "squad_cliente": "squad_cliente",
    "squad-cliente": "squad_cliente",
    "versus": "squad_versus",
    "squad_versus": "squad_versus",
    "squad-versus": "squad_versus",
    "engineering": "engineering",
    "engenharia": "engineering",
    "squad_engenharia": "engineering",
    "squad-engenharia": "engineering",
}


_SQUAD_CLIENTE_HARNESSES = (
    RuntimeHarnessSpec(
        key="harness_coordenador_cliente_v1",
        label="Harness Coordenador do Squad Cliente",
        business_role="coordenação assistida e roteamento inicial",
    ),
    RuntimeHarnessSpec(
        key="harness_comercial_cliente_v1",
        label="Harness Comercial do Squad Cliente",
        business_role="apoio comercial e gestão da jornada de vendas",
    ),
    RuntimeHarnessSpec(
        key="harness_operacional_cliente_v1",
        label="Harness Operacional do Squad Cliente",
        business_role="organização da operação e execução do dia a dia",
    ),
    RuntimeHarnessSpec(
        key="harness_admfin_cliente_v1",
        label="Harness Adm/Financeiro do Squad Cliente",
        business_role="apoio administrativo e financeiro assistido",
    ),
    RuntimeHarnessSpec(
        key="harness_estrategico_cliente_v1",
        label="Harness Estratégico do Squad Cliente",
        business_role="síntese estratégica e priorização executiva",
    ),
    RuntimeHarnessSpec(
        key="harness_pessoas_capacidade_cliente_v1",
        label="Harness Pessoas/Capacidade do Squad Cliente",
        business_role="capacidade, pessoas e alocação operacional",
    ),
)

_SQUAD_VERSUS_HARNESSES = (
    RuntimeHarnessSpec(
        key="harness_coordenador_versus_v1",
        label="Harness Coordenador do Squad Versus",
        business_role="coordenação consultiva e roteamento metodológico",
    ),
    RuntimeHarnessSpec(
        key="harness_strategist_versus_v1",
        label="Harness Strategist Versus",
        business_role="direção estratégica, priorização e visão de crescimento",
    ),
    RuntimeHarnessSpec(
        key="harness_pmo_controller_versus_v1",
        label="Harness PMO Controller Versus",
        business_role="cadência de execução, governança e follow-up executivo",
    ),
    RuntimeHarnessSpec(
        key="harness_business_architect_versus_v1",
        label="Harness Business Architect Versus",
        business_role="estruturação de processos, desenho operacional e coerência sistêmica",
    ),
    RuntimeHarnessSpec(
        key="harness_operations_versus_v1",
        label="Harness Operations Versus",
        business_role="revisão operacional, disciplina de execução e melhoria contínua",
    ),
    RuntimeHarnessSpec(
        key="harness_followup_collector_versus_v1",
        label="Harness Follow-up Collector Versus",
        business_role="cobrança estruturada, fechamento de pendências e manutenção da cadência",
    ),
    RuntimeHarnessSpec(
        key="harness_performance_analyst_versus_v1",
        label="Harness Performance Analyst Versus",
        business_role="análise de performance, indicadores e sinais executivos",
    ),
    RuntimeHarnessSpec(
        key="harness_finance_versus_v1",
        label="Harness Finance Versus",
        business_role="controladoria, leitura financeira controlada e crítica econômico-financeira",
    ),
    RuntimeHarnessSpec(
        key="harness_auditor_versus_v1",
        label="Harness Auditor Versus",
        business_role="auditoria, conformidade e leitura crítica read-only",
    ),
)

_SQUAD_ENGENHARIA_HARNESSES = (
    RuntimeHarnessSpec(
        key="harness_coordenador_engenharia_v1",
        label="Harness Coordenador do Squad de Engenharia",
        business_role="triagem técnica, roteamento e coordenação disciplinada da execução",
    ),
    RuntimeHarnessSpec(
        key="harness_arquiteto_engenharia_v1",
        label="Harness Arquiteto de Engenharia",
        business_role="arquitetura, boundary, segurança e coerência estrutural",
    ),
    RuntimeHarnessSpec(
        key="harness_frontend_engenharia_v1",
        label="Harness Frontend de Engenharia",
        business_role="UX, templates, interface e experiência server-rendered",
    ),
    RuntimeHarnessSpec(
        key="harness_backend_api_engenharia_v1",
        label="Harness Backend API de Engenharia",
        business_role="contratos REST/MCP, schemas e superfícies de entrada",
    ),
    RuntimeHarnessSpec(
        key="harness_backend_service_engenharia_v1",
        label="Harness Backend Service de Engenharia",
        business_role="regra de negócio determinística e services reutilizáveis",
    ),
    RuntimeHarnessSpec(
        key="harness_ai_engineer_engenharia_v1",
        label="Harness AI Engineer de Engenharia",
        business_role="LangGraph, MCP, agentes, RAG e integrações inteligentes",
    ),
    RuntimeHarnessSpec(
        key="harness_dba_engenharia_v1",
        label="Harness DBA de Engenharia",
        business_role="PostgreSQL, modelos, migrações, queries e performance",
    ),
    RuntimeHarnessSpec(
        key="harness_qa_automation_engenharia_v1",
        label="Harness QA Automation de Engenharia",
        business_role="smoke, regressão, evidência e validação disciplinada",
    ),
)


_RUNTIME_PROFILES = {
    "squad_cliente": RuntimeProfileSpec(
        key="squad_cliente",
        label="Squad Cliente",
        default_surface="user",
        allowed_surfaces=("user",),
        actor_type="client_agent",
        family_key="squad_cliente",
        family_label="Squad Cliente",
        default_harness_key="harness_coordenador_cliente_v1",
        default_harness_label="Harness Coordenador do Squad Cliente",
        harnesses=_SQUAD_CLIENTE_HARNESSES,
        requires_training=True,
        supports_personal_token=True,
    ),
    "squad_versus": RuntimeProfileSpec(
        key="squad_versus",
        label="Squad Versus",
        default_surface="admin",
        allowed_surfaces=("admin", "analytics"),
        actor_type="versus_operator",
        family_key="squad_versus",
        family_label="Squad Versus",
        default_harness_key="harness_coordenador_versus_v1",
        default_harness_label="Harness Coordenador do Squad Versus",
        harnesses=_SQUAD_VERSUS_HARNESSES,
        requires_training=True,
        supports_personal_token=False,
    ),
    "engineering": RuntimeProfileSpec(
        key="engineering",
        label="Squad de Engenharia",
        default_surface="ops",
        allowed_surfaces=("ops", "admin", "analytics"),
        actor_type="engineering_operator",
        family_key="engineering",
        family_label="Squad de Engenharia",
        default_harness_key="harness_coordenador_engenharia_v1",
        default_harness_label="Harness Coordenador do Squad de Engenharia",
        harnesses=_SQUAD_ENGENHARIA_HARNESSES,
        requires_training=True,
        supports_personal_token=False,
    ),
}


def normalize_runtime_profile(runtime_profile: str | None) -> str | None:
    normalized = str(runtime_profile or "").strip().lower()
    if not normalized:
        return None
    return _RUNTIME_PROFILE_ALIASES.get(normalized, normalized)


def get_runtime_profile_spec(runtime_profile: str | None) -> RuntimeProfileSpec | None:
    normalized = normalize_runtime_profile(runtime_profile)
    if normalized is None:
        return None
    return _RUNTIME_PROFILES.get(normalized)


__all__ = [
    "RuntimeHarnessSpec",
    "RuntimeProfileSpec",
    "get_runtime_profile_spec",
    "normalize_runtime_profile",
]
