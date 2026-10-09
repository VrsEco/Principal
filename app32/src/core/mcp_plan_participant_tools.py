from __future__ import annotations

from typing import Any, Optional

from services.plan_participant_sync_service import PlanParticipantSyncService
from src.core.mcp_http_auth import get_http_actor_role
from src.core.mcp_session_actor import session_user_id
from src.intelligence.mcp_contracts import MCPErrorDetail, MCPErrorEnvelope, MCPResponseMeta, MCPSuccessEnvelope


def _meta(company_id: int, user_id: int | None) -> MCPResponseMeta:
    return MCPResponseMeta(
        domain="strategy",
        operation="plan_participants.sync",
        scope="mcp_user",
        company_id=company_id,
        user_id=user_id,
        actor_role=get_http_actor_role(),
        capability="strategy.plan_participants.sync",
        human_gate_required=True,
        permissions=["plan.participants.create", "plan.section.update"],
        tags=["strategy", "planning", "participants", "tenant_safe", "human_gate"],
    )


def register_plan_participant_tools(mcp: Any) -> None:
    @mcp.tool()
    def sync_plan_participants_tool(
        company_id: int,
        plan_id: int,
        owner_name: str,
    ) -> dict[str, Any]:
        """Inclui todos os colaboradores ativos do tenant no plano e define um owner oficial."""
        user_id = session_user_id()
        if user_id is None:
            return MCPErrorEnvelope(
                error=MCPErrorDetail(code="plan_participants_forbidden", message="Usuário autenticado não identificado."),
                meta=_meta(company_id, None),
            ).model_dump(mode="json")
        try:
            data = PlanParticipantSyncService.execute(
                company_id=company_id,
                plan_id=plan_id,
                owner_name=owner_name,
                confirmed_mutation=True,  # a aprovação, quando exigida, é do runtime (mcp_gate_policy), não do cliente
                user_id=user_id,
            )
            return MCPSuccessEnvelope[Any](data=data, meta=_meta(company_id, user_id)).model_dump(mode="json")
        except Exception as exc:
            code = "plan_participants_forbidden" if isinstance(exc, PermissionError) else "plan_participants_invalid_request"
            return MCPErrorEnvelope(
                error=MCPErrorDetail(code=code, message=str(exc)),
                meta=_meta(company_id, user_id),
            ).model_dump(mode="json")


__all__ = ["register_plan_participant_tools"]
