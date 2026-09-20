"""Leituras MCP tenant-safe do módulo Auditoria Interna.

P1 é deliberadamente read-only: pontos e achados continuam dependendo da
triagem humana na interface oficial antes de qualquer mutação.
"""

from __future__ import annotations

from typing import Any, Optional


_MAX_LIMIT = 100


def _validated_limit(limit: int) -> int:
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise ValueError("limit deve ser um inteiro.")
    if limit < 1 or limit > _MAX_LIMIT:
        raise ValueError(f"limit deve estar entre 1 e {_MAX_LIMIT}.")
    return limit


def register_internal_audit_mcp_tools(mcp: Any) -> None:
    """Registra somente capacidades de leitura da Auditoria Interna."""

    @mcp.tool()
    def get_internal_audit_summary(company_id: int) -> dict[str, Any]:
        """Retorna contadores agregados da Auditoria Interna da empresa ativa."""

        from services.internal_audit_service import InternalAuditService

        return {
            "company_id": company_id,
            "summary": InternalAuditService.summary(company_id),
        }

    @mcp.tool()
    def list_internal_audit_points(
        company_id: int,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        """Lista pontos de auditoria do tenant; não cria nem altera registros."""

        from services.internal_audit_service import InternalAuditService

        bounded_limit = _validated_limit(limit)
        items = InternalAuditService.list_points(company_id, status=status)
        return {
            "company_id": company_id,
            "status": status,
            "limit": bounded_limit,
            "returned": min(len(items), bounded_limit),
            "items": items[:bounded_limit],
        }

    @mcp.tool()
    def list_internal_audit_findings(
        company_id: int,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        """Lista achados de auditoria do tenant; não cria nem altera registros."""

        from services.internal_audit_service import InternalAuditService

        bounded_limit = _validated_limit(limit)
        items = InternalAuditService.list_findings(company_id, status=status)
        return {
            "company_id": company_id,
            "status": status,
            "limit": bounded_limit,
            "returned": min(len(items), bounded_limit),
            "items": items[:bounded_limit],
        }


__all__ = ["register_internal_audit_mcp_tools"]
