from __future__ import annotations

from src.intelligence.mcp_contracts import APP32_ALLOWED_ANALYSIS_CATALOG
from src.intelligence.mcp_contracts.base import MCPErrorDetail, MCPErrorEnvelope, MCPResponseMeta


def register_analysis_catalog_tools(mcp: object) -> None:
    @mcp.tool(
        name="describe_app32_analysis_catalog_tool",
        description="Descreve o catálogo versionado de análises permitidas por IA no analytics MCP do APP32.",
    )
    def describe_app32_analysis_catalog_tool(analysis_id: str | None = None) -> dict:
        meta = MCPResponseMeta(
            domain="analytics",
            operation="describe_analysis_catalog",
            scope="mcp_analytics",
            tenant_safe=True,
            human_gate_required=False,
            permissions=["analytics.catalog.read"],
            tags=["manifest", "analytics", "governance"],
        )

        if not analysis_id:
            return {
                "success": True,
                "message": "Catálogo de análises permitidas por IA.",
                "data": APP32_ALLOWED_ANALYSIS_CATALOG.model_dump(mode="json"),
                "meta": meta.model_dump(mode="json"),
            }

        analysis = APP32_ALLOWED_ANALYSIS_CATALOG.get_analysis(analysis_id)
        if analysis is None:
            error = MCPErrorEnvelope(
                error=MCPErrorDetail(
                    code="analysis_catalog_not_found",
                    message="Análise não encontrada no catálogo permitido do APP32.",
                    details={"analysis_id": analysis_id},
                    retryable=False,
                ),
                meta=meta,
            )
            return error.model_dump(mode="json")

        return {
            "success": True,
            "message": "Contrato de análise permitido.",
            "data": analysis.model_dump(mode="json"),
            "meta": meta.model_dump(mode="json"),
        }


__all__ = ["register_analysis_catalog_tools"]
