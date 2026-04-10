from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from .base import MCPSuccessEnvelope, _StrictModel


UsageDashboardSurface = Literal["user", "admin", "analytics", "ops", "sapiens", "mcp"]
UsageDashboardMetricKind = Literal["counter", "ratio", "latency", "timeseries", "table"]
UsageDashboardDataSource = Literal["ai_audit_log", "workflow_usage", "agent_messages", "tool_catalog"]


class UsageDashboardMetric(_StrictModel):
    metric_id: str = Field(min_length=4, max_length=80)
    title: str = Field(min_length=6, max_length=140)
    kind: UsageDashboardMetricKind
    source: UsageDashboardDataSource
    description: str = Field(min_length=16, max_length=320)
    required_filters: list[str] = Field(default_factory=list, min_length=1)
    dimensions: list[str] = Field(default_factory=list, min_length=1)
    allowed_surfaces: list[UsageDashboardSurface] = Field(default_factory=list, min_length=1)
    sensitive: bool = False
    max_rows: int = Field(default=200, ge=1, le=1000)

    @model_validator(mode="after")
    def _validate_metric(self):
        if "company_id" not in self.required_filters:
            raise ValueError("Métrica de uso IA/MCP deve exigir company_id.")
        if self.source == "ai_audit_log" and "occurred_at" not in self.dimensions:
            raise ValueError("Métrica de auditoria IA/MCP deve dimensionalizar por occurred_at.")
        return self


class UsageDashboardPanel(_StrictModel):
    panel_id: str = Field(min_length=4, max_length=80)
    title: str = Field(min_length=6, max_length=140)
    objective: str = Field(min_length=16, max_length=320)
    metrics: list[str] = Field(default_factory=list, min_length=1)
    default_visualization: Literal["cards", "line", "bar", "table", "heatmap"] = "table"
    refresh_policy: str = Field(min_length=8, max_length=240)


class UsageDashboardManifest(_StrictModel):
    version: str = Field(default="app32.ai-mcp.usage-dashboard.v1", min_length=1, max_length=80)
    title: str = "Dashboard e Relatório de Uso IA/MCP"
    tenant_scope_required: bool = True
    sql_freeform_allowed: bool = False
    required_global_filters: list[str] = Field(
        default_factory=lambda: ["company_id", "date_from", "date_to"],
        min_length=1,
    )
    data_sources: list[UsageDashboardDataSource] = Field(default_factory=list, min_length=1)
    metrics: list[UsageDashboardMetric] = Field(default_factory=list, min_length=1)
    panels: list[UsageDashboardPanel] = Field(default_factory=list, min_length=1)
    operational_alerts: list[str] = Field(default_factory=list, min_length=1)
    access_rules: list[str] = Field(default_factory=list, min_length=1)

    @model_validator(mode="after")
    def _validate_manifest(self):
        if not self.tenant_scope_required:
            raise ValueError("Dashboard IA/MCP deve exigir tenant_scope_required=True.")
        if self.sql_freeform_allowed:
            raise ValueError("Dashboard IA/MCP não pode liberar SQL livre.")
        metric_ids = {metric.metric_id for metric in self.metrics}
        for panel in self.panels:
            missing = set(panel.metrics) - metric_ids
            if missing:
                raise ValueError(f"Painel referencia métricas inexistentes: {sorted(missing)}")
        return self

    def get_metric(self, metric_id: str) -> UsageDashboardMetric | None:
        normalized = str(metric_id or "").strip().lower()
        for metric in self.metrics:
            if metric.metric_id == normalized:
                return metric
        return None


UsageDashboardEnvelope = MCPSuccessEnvelope[UsageDashboardManifest | UsageDashboardMetric]


def build_usage_dashboard_manifest() -> UsageDashboardManifest:
    return UsageDashboardManifest(
        data_sources=["ai_audit_log", "workflow_usage", "agent_messages", "tool_catalog"],
        metrics=[
            UsageDashboardMetric(
                metric_id="ai_mcp_calls_total",
                title="Chamadas IA/MCP por período",
                kind="counter",
                source="ai_audit_log",
                description="Total de eventos de runtime Sapiens e tools MCP por empresa e período.",
                required_filters=["company_id", "date_from", "date_to"],
                dimensions=["occurred_at", "runtime", "scope", "surface", "tool_name", "status"],
                allowed_surfaces=["admin", "analytics", "ops", "mcp", "sapiens"],
            ),
            UsageDashboardMetric(
                metric_id="ai_mcp_error_rate",
                title="Taxa de erro IA/MCP",
                kind="ratio",
                source="ai_audit_log",
                description="Percentual de eventos com status de erro, bloqueio ou falha por runtime/tool.",
                required_filters=["company_id", "date_from", "date_to"],
                dimensions=["occurred_at", "runtime", "tool_name", "status", "domain"],
                allowed_surfaces=["admin", "analytics", "ops"],
            ),
            UsageDashboardMetric(
                metric_id="mcp_tool_usage_by_domain",
                title="Uso de tools por domínio",
                kind="table",
                source="ai_audit_log",
                description="Ranking de tools MCP por domínio, surface, status e volume de chamadas.",
                required_filters=["company_id", "date_from", "date_to"],
                dimensions=["occurred_at", "domain", "tool_name", "scope", "status"],
                allowed_surfaces=["admin", "analytics", "mcp"],
                max_rows=300,
            ),
            UsageDashboardMetric(
                metric_id="workflow_resolution_trace",
                title="Resolução de workflows pelo Sapiens",
                kind="timeseries",
                source="workflow_usage",
                description="Evolução de interceptações, rotas de descoberta, confiança e status de workflows.",
                required_filters=["company_id", "date_from", "date_to"],
                dimensions=["company_id", "channel", "route_source", "intercept_stage", "status", "confidence_route"],
                allowed_surfaces=["admin", "analytics", "sapiens"],
            ),
            UsageDashboardMetric(
                metric_id="agent_messages_volume",
                title="Volume de mensagens por canal",
                kind="counter",
                source="agent_messages",
                description="Volume de mensagens inbound/outbound por canal, agente e período.",
                required_filters=["company_id", "date_from", "date_to"],
                dimensions=["company_id", "channel", "direction", "agent_type", "model_used"],
                allowed_surfaces=["admin", "analytics", "sapiens"],
            ),
            UsageDashboardMetric(
                metric_id="catalog_surface_coverage",
                title="Cobertura de catálogo por surface",
                kind="table",
                source="tool_catalog",
                description="Quantidade de capabilities por surface, domínio, risco e permissão.",
                required_filters=["company_id"],
                dimensions=["scope", "domain", "risk", "permission", "tool_name"],
                allowed_surfaces=["admin", "analytics", "mcp"],
            ),
        ],
        panels=[
            UsageDashboardPanel(
                panel_id="executive_overview",
                title="Visão executiva IA/MCP",
                objective="Acompanhar volume, taxa de erro, canais e evolução de uso por empresa.",
                metrics=["ai_mcp_calls_total", "ai_mcp_error_rate", "agent_messages_volume"],
                default_visualization="cards",
                refresh_policy="Atualização sob demanda e recorte padrão de 7 dias.",
            ),
            UsageDashboardPanel(
                panel_id="mcp_operations",
                title="Operação MCP por domínio e tool",
                objective="Monitorar uso de tools MCP, status, domínio e cobertura de catálogo.",
                metrics=["mcp_tool_usage_by_domain", "catalog_surface_coverage"],
                default_visualization="table",
                refresh_policy="Atualização sob demanda antes/depois de releases MCP.",
            ),
            UsageDashboardPanel(
                panel_id="sapiens_workflow_resolution",
                title="Resolução de workflows Sapiens",
                objective="Avaliar interceptação, descoberta, confiança e resolução dos workflows conversacionais.",
                metrics=["workflow_resolution_trace", "agent_messages_volume"],
                default_visualization="line",
                refresh_policy="Atualização sob demanda por período e canal.",
            ),
        ],
        operational_alerts=[
            "Taxa de erro IA/MCP acima de 5% no período selecionado.",
            "Evento bloqueado por tenant/security em qualquer surface produtiva.",
            "Uso de tool sensível fora da surface esperada.",
            "Queda abrupta de interceptação de workflows após deploy.",
        ],
        access_rules=[
            "Dashboard exige company_id e período explícitos.",
            "Perfis não administrativos não acessam visão consolidada multi-tool.",
            "Dados sensíveis devem ser agregados; não expor conteúdo integral de prompt/mensagem por padrão.",
            "SQL livre é proibido; usar read models ou queries whitelisted.",
        ],
    )


APP32_USAGE_DASHBOARD_MANIFEST = build_usage_dashboard_manifest()


__all__ = [
    "APP32_USAGE_DASHBOARD_MANIFEST",
    "UsageDashboardDataSource",
    "UsageDashboardEnvelope",
    "UsageDashboardManifest",
    "UsageDashboardMetric",
    "UsageDashboardMetricKind",
    "UsageDashboardPanel",
    "UsageDashboardSurface",
    "build_usage_dashboard_manifest",
]
