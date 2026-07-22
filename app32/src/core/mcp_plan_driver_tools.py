from __future__ import annotations

from typing import Any, Optional

from services.plan_driver_mcp_service import PlanDriverMCPService
from src.core.mcp_http_auth import get_http_actor_role, get_http_request_context
from src.intelligence.mcp_contracts import MCPErrorDetail, MCPErrorEnvelope, MCPResponseMeta, MCPSuccessEnvelope


def _meta(company_id: int, user_id: int | None) -> MCPResponseMeta:
    return MCPResponseMeta(
        domain="strategy",
        operation="plan_driver.create",
        scope="mcp_user",
        company_id=company_id,
        user_id=user_id,
        actor_role=get_http_actor_role(),
        capability="strategy.plan_driver.create",
        human_gate_required=True,
        permissions=["plan.section.update"],
        tags=["strategy", "planning", "driver", "tenant_safe", "human_gate"],
    )


def register_plan_driver_tools(mcp: Any) -> None:
    @mcp.tool()
    def create_single_plan_driver_tool(
        company_id: int,
        plan_id: int,
        description: str,
        review_date: Optional[str] = None,
        confirmed_mutation: bool = False,
        user_id: Optional[int] = None,
    ) -> dict[str, Any]:
        """Cadastra o único direcionador confirmado de um planejamento growth."""
        context = dict(get_http_request_context() or {})
        authenticated_user_id = context.get("user_id")
        if authenticated_user_id not in (None, ""):
            authenticated_user_id = int(authenticated_user_id)
            if user_id not in (None, authenticated_user_id):
                return MCPErrorEnvelope(
                    error=MCPErrorDetail(code="plan_driver_forbidden", message="user_id diverge do usuário autenticado."),
                    meta=_meta(company_id, authenticated_user_id),
                ).model_dump(mode="json")
            user_id = authenticated_user_id
        try:
            data = PlanDriverMCPService.create_single_driver(
                company_id=company_id,
                plan_id=plan_id,
                description=description,
                review_date=review_date,
                confirmed_mutation=confirmed_mutation,
                user_id=user_id,
            )
            return MCPSuccessEnvelope[Any](data=data, meta=_meta(company_id, user_id)).model_dump(mode="json")
        except Exception as exc:
            code = "plan_driver_forbidden" if isinstance(exc, PermissionError) else "plan_driver_invalid_request"
            return MCPErrorEnvelope(
                error=MCPErrorDetail(code=code, message=str(exc)),
                meta=_meta(company_id, user_id),
            ).model_dump(mode="json")


__all__ = ["register_plan_driver_tools"]
