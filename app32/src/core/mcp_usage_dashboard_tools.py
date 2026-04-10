from __future__ import annotations

from typing import Any, Optional

from src.intelligence.mcp_contracts import (
    APP32_USAGE_DASHBOARD_MANIFEST,
    MCPErrorDetail,
    MCPErrorEnvelope,
    MCPResponseMeta,
    MCPSuccessEnvelope,
)


def _meta(operation: str, metric_id: str | None = None) -> MCPResponseMeta:
    return MCPResponseMeta(
        domain="mcp_usage_dashboard",
        operation=operation,
        scope="mcp_analytics",
        capability=f"mcp_usage_dashboard.{operation}",
        permissions=["mcp.usage_dashboard.read"],
        tags=["usage", "dashboard", "ai", "mcp", *(["metric:" + metric_id] if metric_id else [])],
    )


def _success(operation: str, data: Any, metric_id: str | None = None) -> dict[str, Any]:
    return MCPSuccessEnvelope[Any](
        data=data,
        meta=_meta(operation, metric_id=metric_id),
    ).model_dump(mode="json")


def _error(operation: str, message: str, metric_id: str | None = None) -> dict[str, Any]:
    return MCPErrorEnvelope(
        error=MCPErrorDetail(code="usage_dashboard_metric_not_found", message=message),
        meta=_meta(operation, metric_id=metric_id),
    ).model_dump(mode="json")


def register_usage_dashboard_tools(mcp: Any) -> None:
    """Registra tools MCP de descoberta do dashboard/relatório de uso IA/MCP."""

    @mcp.tool()
    def describe_app32_usage_dashboard_tool(metric_id: Optional[str] = None) -> dict[str, Any]:
        """
        Descreve a especificação canônica do dashboard/relatório de uso IA/MCP
        e, opcionalmente, uma métrica específica.
        """
        if not metric_id:
            return _success(
                "usage_dashboard.describe",
                APP32_USAGE_DASHBOARD_MANIFEST.model_dump(mode="json"),
            )

        normalized = metric_id.strip().lower()
        metric = APP32_USAGE_DASHBOARD_MANIFEST.get_metric(normalized)
        if metric is None:
            return _error(
                "usage_dashboard.describe",
                f"Métrica de dashboard IA/MCP não encontrada: {metric_id}.",
                metric_id=normalized or None,
            )

        return _success(
            "usage_dashboard.describe",
            metric.model_dump(mode="json"),
            metric_id=metric.metric_id,
        )


__all__ = ["register_usage_dashboard_tools"]
