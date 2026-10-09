from __future__ import annotations

from typing import Any, Optional

from services.plan_global_okr_correction_service import PlanGlobalOKRCorrectionService
from src.core.mcp_http_auth import get_http_actor_role
from src.core.mcp_session_actor import session_user_id
from src.intelligence.mcp_contracts import MCPErrorDetail, MCPErrorEnvelope, MCPResponseMeta, MCPSuccessEnvelope


def _meta(company_id: int, user_id: int | None) -> MCPResponseMeta:
    return MCPResponseMeta(
        domain="strategy",
        operation="plan_global_okrs.correct",
        scope="mcp_user",
        company_id=company_id,
        user_id=user_id,
        actor_role=get_http_actor_role(),
        capability="strategy.plan_global_okrs.correct",
        human_gate_required=True,
        permissions=["okrs.global.update", "okrs.area.update", "plan.section.update"],
        tags=["strategy", "planning", "global_okr", "correction", "tenant_safe", "human_gate"],
    )


def register_plan_global_okr_correction_tools(mcp: Any) -> None:
    @mcp.tool()
    def correct_plan_global_okrs_tool(
        company_id: int,
        plan_id: int,
        revenue_objective: str,
        profit_objective: str,
        derived_area_okr_ids: list[int],
        confirmed_mutation: bool = False,
    ) -> dict[str, Any]:
        """Corrige os dois OKRs Globais e aponta os OKRs de Área para o objetivo de faturamento."""
        user_id = session_user_id()
        if user_id is None:
            return MCPErrorEnvelope(
                error=MCPErrorDetail(code="plan_global_okrs_correction_forbidden", message="Usuário autenticado não identificado."),
                meta=_meta(company_id, None),
            ).model_dump(mode="json")
        try:
            data = PlanGlobalOKRCorrectionService.execute(
                company_id=company_id,
                plan_id=plan_id,
                revenue_objective=revenue_objective,
                profit_objective=profit_objective,
                derived_area_okr_ids=derived_area_okr_ids,
                confirmed_mutation=confirmed_mutation,
                user_id=user_id,
            )
            return MCPSuccessEnvelope[Any](data=data, meta=_meta(company_id, user_id)).model_dump(mode="json")
        except Exception as exc:
            code = "plan_global_okrs_correction_forbidden" if isinstance(exc, PermissionError) else "plan_global_okrs_correction_invalid_request"
            return MCPErrorEnvelope(
                error=MCPErrorDetail(code=code, message=str(exc)),
                meta=_meta(company_id, user_id),
            ).model_dump(mode="json")


__all__ = ["register_plan_global_okr_correction_tools"]
