from __future__ import annotations

from typing import Any, Optional

from services.sector_strategy_structure_service import SectorStrategyStructureService
from src.core.mcp_http_auth import get_http_actor_role, get_http_request_context
from src.intelligence.mcp_contracts import MCPErrorDetail, MCPErrorEnvelope, MCPResponseMeta, MCPSuccessEnvelope


def _meta(*, company_id: int | None = None, user_id: int | None = None) -> MCPResponseMeta:
    return MCPResponseMeta(
        domain="strategy",
        operation="sector_structure.create",
        scope="mcp_user",
        company_id=company_id,
        user_id=user_id,
        actor_role=get_http_actor_role(),
        capability="strategy.sector_structure.create",
        human_gate_required=True,
        permissions=["okrs.area.create", "okrs.key_results.create", "project.create"],
        tags=["strategy", "sector_structure", "tenant_safe", "transactional", "human_gate"],
    )


def register_sector_strategy_tools(mcp: Any) -> None:
    @mcp.tool()
    def create_sector_okr_structure_tool(
        company_id: int,
        payload: dict[str, Any],
        confirmed_mutation: bool = False,
        user_id: Optional[int] = None,
    ) -> dict[str, Any]:
        """Cadastra atomicamente OKRs setoriais, KRs propostos e iniciativas vinculadas."""
        context = dict(get_http_request_context() or {})
        authenticated_user_id = context.get("user_id")
        if authenticated_user_id not in (None, ""):
            authenticated_user_id = int(authenticated_user_id)
            if user_id not in (None, authenticated_user_id):
                return MCPErrorEnvelope(
                    error=MCPErrorDetail(code="sector_structure_forbidden", message="user_id diverge do usuário autenticado."),
                    meta=_meta(company_id=company_id, user_id=authenticated_user_id),
                ).model_dump(mode="json")
            user_id = authenticated_user_id
        try:
            data = SectorStrategyStructureService.execute(
                company_id=company_id,
                payload=payload,
                confirmed_mutation=confirmed_mutation,
                user_id=user_id,
            )
            return MCPSuccessEnvelope[Any](data=data, meta=_meta(company_id=company_id, user_id=user_id)).model_dump(mode="json")
        except Exception as exc:
            code = "sector_structure_forbidden" if isinstance(exc, PermissionError) else "sector_structure_invalid_request"
            return MCPErrorEnvelope(
                error=MCPErrorDetail(code=code, message=str(exc)),
                meta=_meta(company_id=company_id, user_id=user_id),
            ).model_dump(mode="json")


__all__ = ["register_sector_strategy_tools"]
