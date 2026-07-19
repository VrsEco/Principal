from __future__ import annotations

from datetime import date
from typing import Any, Optional

from services.mcp_operation_router_service import McpOperationRouterService
from src.core.mcp_http_auth import get_http_actor_role, get_http_request_context
from src.intelligence.mcp_contracts import MCPErrorDetail, MCPErrorEnvelope, MCPResponseMeta, MCPSuccessEnvelope


def _meta(operation: str, *, company_id: int | None = None, user_id: int | None = None) -> MCPResponseMeta:
    return MCPResponseMeta(
        domain="identity_self_service",
        operation=operation,
        scope="mcp_user",
        company_id=company_id,
        user_id=user_id,
        actor_role=get_http_actor_role(),
        capability=f"governance.{operation}",
        permissions=["identity_self_service.read"],
        tags=["routing", "workflow_first", "tenant_safe"],
    )


def register_operation_router_tools(mcp: Any) -> None:
    @mcp.tool()
    def resolve_app32_operation_tool(
        request_text: str,
        company_id: Optional[int] = None,
        reference_date: Optional[str] = None,
    ) -> dict[str, Any]:
        """Resolve rapidamente domínio, intenção, harness e tool ativa para um pedido em linguagem natural."""

        context = dict(get_http_request_context() or {})
        active_company_id = context.get("company_id")
        resolved_company_id = company_id if company_id is not None else active_company_id
        accessible = {int(value) for value in (context.get("accessible_company_ids") or []) if str(value).isdigit()}
        if not isinstance(resolved_company_id, int) or isinstance(resolved_company_id, bool):
            return MCPErrorEnvelope(
                error=MCPErrorDetail(code="mcp_operation_company_required", message="Selecione uma empresa antes de rotear a solicitação."),
                meta=_meta("resolve_app32_operation_tool", user_id=context.get("user_id")),
            ).model_dump(mode="json")
        if accessible and resolved_company_id not in accessible:
            return MCPErrorEnvelope(
                error=MCPErrorDetail(code="mcp_operation_company_forbidden", message="Empresa fora do escopo autorizado da sessão."),
                meta=_meta("resolve_app32_operation_tool", company_id=resolved_company_id, user_id=context.get("user_id")),
            ).model_dump(mode="json")

        parsed_reference = None
        if reference_date:
            try:
                parsed_reference = date.fromisoformat(reference_date)
            except ValueError:
                return MCPErrorEnvelope(
                    error=MCPErrorDetail(code="mcp_operation_invalid_reference_date", message="reference_date deve usar YYYY-MM-DD."),
                    meta=_meta("resolve_app32_operation_tool", company_id=resolved_company_id, user_id=context.get("user_id")),
                ).model_dump(mode="json")
        try:
            route = McpOperationRouterService.resolve(
                request_text=request_text,
                company_id=resolved_company_id,
                current_harness_key=str(context.get("harness_key") or "").strip() or None,
                reference_date=parsed_reference,
            )
        except ValueError as exc:
            return MCPErrorEnvelope(
                error=MCPErrorDetail(code="mcp_operation_invalid_request", message=str(exc)),
                meta=_meta("resolve_app32_operation_tool", company_id=resolved_company_id, user_id=context.get("user_id")),
            ).model_dump(mode="json")
        route["catalog_scope"] = "effective_runtime_only"
        return MCPSuccessEnvelope[Any](
            data=route,
            meta=_meta("resolve_app32_operation_tool", company_id=resolved_company_id, user_id=context.get("user_id")),
        ).model_dump(mode="json")


__all__ = ["register_operation_router_tools"]
