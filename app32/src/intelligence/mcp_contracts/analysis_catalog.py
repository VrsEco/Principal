from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from .base import MCPSuccessEnvelope, _StrictModel
from .profiles import MCPAllowedSurface, MCPMutationRisk, MCPProfileName


AnalysisDomain = Literal["strategy", "finance", "workload", "routine", "projects", "meetings", "analytics"]
AnalysisStatus = Literal["ready", "partial", "planned"]
AnalysisOutputMode = Literal["summary", "table", "timeseries", "diagnostic"]


class AllowedAnalysisContract(_StrictModel):
    analysis_id: str = Field(min_length=4, max_length=80)
    title: str = Field(min_length=8, max_length=140)
    domain: AnalysisDomain
    description: str = Field(min_length=16, max_length=320)
    status: AnalysisStatus = "planned"
    allowed_profiles: list[MCPProfileName] = Field(default_factory=list, min_length=1)
    allowed_surfaces: list[MCPAllowedSurface] = Field(default_factory=list, min_length=1)
    required_filters: list[str] = Field(default_factory=list, min_length=1)
    optional_filters: list[str] = Field(default_factory=list)
    allowed_dimensions: list[str] = Field(default_factory=list, min_length=1)
    output_modes: list[AnalysisOutputMode] = Field(default_factory=list, min_length=1)
    capability_names: list[str] = Field(default_factory=list)
    required_read_models: list[str] = Field(default_factory=list)
    max_rows: int = Field(default=200, ge=1, le=1000)
    risk: MCPMutationRisk = "medium"
    requires_explicit_company_id: bool = True
    cross_tenant_allowed: bool = False
    sql_freeform_allowed: bool = False
    human_gate_required: bool = False
    forbidden_patterns: list[str] = Field(default_factory=list, min_length=1)

    @model_validator(mode="after")
    def _validate_contract(self):
        if self.cross_tenant_allowed:
            raise ValueError("Catálogo de análises permitidas por IA não pode liberar cross-tenant.")
        if not self.requires_explicit_company_id:
            raise ValueError("Análises permitidas por IA exigem company_id explícito.")
        if self.sql_freeform_allowed:
            raise ValueError("Catálogo não deve liberar SQL livre; usar read models whitelisted.")
        if self.domain == "finance" and not {"administrador", "admin_tecnico"}.issuperset(self.allowed_profiles):
            raise ValueError("Análises financeiras ficam restritas a perfis administrativos.")
        if self.domain == "finance" and "analytics" not in self.allowed_surfaces:
            raise ValueError("Análises financeiras devem passar pela surface analytics.")
        return self


class AllowedAnalysisCatalogManifest(_StrictModel):
    version: str = Field(default="app32.mcp.analysis-catalog.v1", min_length=1, max_length=80)
    analyses: list[AllowedAnalysisContract] = Field(default_factory=list, min_length=1)

    def get_analysis(self, analysis_id: str) -> AllowedAnalysisContract | None:
        normalized = str(analysis_id or "").strip().lower()
        normalized = {
            "strategy_alignment_n1": "strategic_alignment_n1",
        }.get(normalized, normalized)
        for analysis in self.analyses:
            if analysis.analysis_id == normalized:
                return analysis
        return None


AllowedAnalysisCatalogEnvelope = MCPSuccessEnvelope[AllowedAnalysisCatalogManifest | AllowedAnalysisContract]


def build_allowed_analysis_catalog_manifest() -> AllowedAnalysisCatalogManifest:
    return AllowedAnalysisCatalogManifest(
        analyses=[
            AllowedAnalysisContract(
                analysis_id="strategy_plan_diagnostics",
                title="Diagnóstico estratégico de planos",
                domain="strategy",
                description="Leitura diagnóstica de planos com foco em seções críticas, lacunas e sinais de atraso.",
                status="ready",
                allowed_profiles=["administrador", "admin_tecnico"],
                allowed_surfaces=["analytics"],
                required_filters=["company_id", "plan_id"],
                optional_filters=["section_code", "status"],
                allowed_dimensions=["plan", "section", "status"],
                output_modes=["summary", "diagnostic"],
                capability_names=["get_plan_diagnostics", "get_plan_diagnostics_read_model"],
                required_read_models=["strategy.plan_diagnostics"],
                max_rows=50,
                risk="medium",
                forbidden_patterns=[
                    "sql livre",
                    "cross-tenant",
                    "mutação de plano",
                ],
            ),
            AllowedAnalysisContract(
                analysis_id="strategic_alignment_n1",
                title="Alinhamento estratégico N1",
                domain="strategy",
                description="Cruza arquitetura de processos com identidade organizacional para mapear alinhamentos e desalinhamentos.",
                status="ready",
                allowed_profiles=["administrador", "admin_tecnico"],
                allowed_surfaces=["analytics"],
                required_filters=["company_id"],
                optional_filters=["process_id", "plan_id"],
                allowed_dimensions=[
                    "process",
                    "objective",
                    "pillar",
                    "value_proposition",
                    "differential",
                    "policy",
                    "indicator",
                ],
                output_modes=["summary", "table", "diagnostic"],
                capability_names=[
                    "get_strategic_alignment_n1_readiness_tool",
                    "analyze_strategic_alignment_n1_tool",
                    "get_strategy_alignment_n1_readiness_tool",
                    "run_strategy_alignment_n1_analysis_tool",
                    "list_strategy_maturation_backlog_tool",
                    "review_strategy_maturation_item_tool",
                ],
                required_read_models=["strategic.alignment_n1"],
                max_rows=300,
                risk="medium",
                forbidden_patterns=[
                    "sql livre",
                    "cross-tenant",
                    "mutação durante análise",
                ],
            ),
            AllowedAnalysisContract(
                analysis_id="workload_team_capacity",
                title="Capacidade e carga de trabalho do time",
                domain="workload",
                description="Análise de capacidade, distribuição e sobrecarga de equipes dentro da empresa-alvo.",
                status="ready",
                allowed_profiles=["administrador", "admin_tecnico"],
                allowed_surfaces=["analytics", "ops"],
                required_filters=["company_id", "team_id"],
                optional_filters=["employee_id", "date_from", "date_to"],
                allowed_dimensions=["team", "employee", "period"],
                output_modes=["summary", "table"],
                capability_names=["list_team_workload", "get_team_workload_read_model"],
                required_read_models=["workload.team_capacity"],
                max_rows=200,
                risk="medium",
                forbidden_patterns=[
                    "sql livre",
                    "cross-tenant",
                    "alteração de alocação",
                ],
            ),
            AllowedAnalysisContract(
                analysis_id="finance_cash_commitments",
                title="Compromissos e pressão de caixa",
                domain="finance",
                description="Leitura consolidada de compromissos financeiros, vencimentos e pressão de caixa por empresa.",
                status="planned",
                allowed_profiles=["administrador", "admin_tecnico"],
                allowed_surfaces=["analytics"],
                required_filters=["company_id", "date_from", "date_to"],
                optional_filters=["cost_center_id", "account_type"],
                allowed_dimensions=["period", "account_type", "cost_center"],
                output_modes=["summary", "table", "timeseries"],
                capability_names=[],
                required_read_models=["finance.cash_commitments", "finance.payables_receivables_rollup"],
                max_rows=300,
                risk="high",
                human_gate_required=True,
                forbidden_patterns=[
                    "sql livre",
                    "cross-tenant",
                    "exposição de credenciais bancárias",
                ],
            ),
            AllowedAnalysisContract(
                analysis_id="projects_execution_risk",
                title="Risco de execução de projetos",
                domain="projects",
                description="Análise de backlog, atrasos, responsáveis e concentração de risco em projetos da empresa.",
                status="partial",
                allowed_profiles=["administrador", "admin_tecnico"],
                allowed_surfaces=["analytics"],
                required_filters=["company_id"],
                optional_filters=["project_id", "assignee_id", "status"],
                allowed_dimensions=["project", "assignee", "status", "deadline"],
                output_modes=["summary", "table"],
                capability_names=["get_projects_execution_risk_read_model"],
                required_read_models=["projects.execution_risk"],
                max_rows=250,
                risk="medium",
                forbidden_patterns=[
                    "sql livre",
                    "cross-tenant",
                    "mudança de status via análise",
                ],
            ),
        ]
    )


APP32_ALLOWED_ANALYSIS_CATALOG = build_allowed_analysis_catalog_manifest()


__all__ = [
    "APP32_ALLOWED_ANALYSIS_CATALOG",
    "AllowedAnalysisCatalogEnvelope",
    "AllowedAnalysisCatalogManifest",
    "AllowedAnalysisContract",
    "AnalysisDomain",
    "AnalysisOutputMode",
    "AnalysisStatus",
    "build_allowed_analysis_catalog_manifest",
]
